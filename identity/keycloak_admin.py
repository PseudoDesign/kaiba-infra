#!/usr/bin/env python3
"""Manage Kaiba's public realm policy and one bounded owner enrollment ceremony.

Credentials are read from files into memory. HTTP failures deliberately omit
response bodies and all commands avoid printing tokens, passwords or action URLs.
The policy reconciler never replaces users or their WebAuthn credentials.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class Refuse(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refuse("Keycloak unexpectedly redirected an administration request")


def private_read(path):
    with open(path, "r", opener=lambda p, f: os.open(p, f | os.O_NOFOLLOW)) as handle:
        mode = os.fstat(handle.fileno())
        credentials_directory = os.environ.get("CREDENTIALS_DIRECTORY")
        systemd_credential = credentials_directory and Path(path).parent == Path(credentials_directory)
        allowed_links = {0, 1} if systemd_credential else {1}
        unsafe_permissions = bool(mode.st_mode & 0o077)
        if systemd_credential:
            # LoadCredential uses 0440 on current systemd. Its private,
            # potentially id-mapped mount enforces access; fstat's group need
            # not equal getegid(). Never allow group writes or world access,
            # and do not relax ordinary runtime-file modes.
            unsafe_permissions = bool(mode.st_mode & 0o037)
        if not stat.S_ISREG(mode.st_mode) or unsafe_permissions or mode.st_nlink not in allowed_links:
            raise Refuse("credential/state file must be private and regular (mode=" + oct(stat.S_IMODE(mode.st_mode)) + ", links=" + str(mode.st_nlink) + ")")
        value = handle.read(65537)
    if len(value) > 65536:
        raise Refuse("credential/state file too large")
    return value


def private_write(path, value):
    temporary = path.with_name(path.name + ".new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


class Admin:
    def __init__(self, url, username, password, realm):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path:
            raise Refuse("administration must use the local loopback listener")
        self.url = url
        self.realm = realm
        self.opener = urllib.request.build_opener(NoRedirect())
        self.token = None
        result = self.request("POST", "/realms/master/protocol/openid-connect/token", form={
            "client_id": "admin-cli", "grant_type": "password",
            "username": username, "password": password,
        })
        self.token = result["access_token"]

    def request(self, method, path, value=None, form=None):
        headers = {"X-Forwarded-Proto": "https", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if value is not None:
            data = json.dumps(value).encode()
            headers["Content-Type"] = "application/json"
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                body = response.read(4 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raise Refuse(f"Keycloak administration request failed (HTTP {error.code})") from None
        if len(body) > 4 * 1024 * 1024:
            raise Refuse("Keycloak administration response exceeded limit")
        return json.loads(body) if body else None

    def api(self, method, path="", value=None):
        return self.request(method, "/admin/realms/" + self.realm + path, value)

    def client(self, name):
        clients = self.api("GET", "/clients?clientId=" + urllib.parse.quote(name))
        exact = [client for client in clients if client["clientId"] == name]
        if len(exact) != 1:
            raise Refuse("managed client missing or ambiguous")
        return exact[0]

    def flow(self, alias):
        flows = [flow for flow in self.api("GET", "/authentication/flows") if flow["alias"] == alias]
        if len(flows) != 1:
            raise Refuse("managed authentication flow missing or ambiguous")
        return flows[0]

    def group(self):
        groups = self.api("GET", "/groups?search=kaiba-ssh-admin&exact=true")
        groups = [group for group in groups if group["name"] == "kaiba-ssh-admin"]
        if len(groups) != 1:
            raise Refuse("managed SSH administrator group missing or ambiguous")
        return groups[0]

    def owner_role(self):
        return self.api("GET", "/roles/kaiba-owner-enrolling")

    def set_enrollment(self, enabled):
        client = self.client("kaiba-owner-enrollment")
        self.api("PUT", "/clients/" + client["id"], {"enabled": enabled})
        if self.client("kaiba-owner-enrollment")["enabled"] != enabled:
            raise Refuse("enrollment client state did not persist")


def check_subset(actual, expected, label):
    for key, value in expected.items():
        observed = actual.get(key)
        if isinstance(value, dict) and isinstance(observed, dict):
            check_subset(observed, value, label + "." + key)
            continue
        if isinstance(value, list) and isinstance(observed, list):
            observed = sorted(observed, key=lambda item: json.dumps(item, sort_keys=True))
            value = sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
        if observed != value:
            raise Refuse(f"managed {label} setting differs: {key}")


def reconcile_scopes(admin, path, wanted, available):
    selected = []
    for name in wanted:
        matches = [scope for scope in available if scope["name"] == name]
        if len(matches) != 1:
            raise Refuse("required client scope missing or ambiguous: " + name)
        selected.append(matches[0])
    actual = admin.api("GET", path)
    for scope in actual:
        if scope["name"] not in wanted:
            admin.api("DELETE", path + "/" + scope["id"])
    for scope in selected:
        if not any(existing["id"] == scope["id"] for existing in actual):
            admin.api("PUT", path + "/" + scope["id"])
    if sorted(scope["name"] for scope in admin.api("GET", path)) != sorted(wanted):
        raise Refuse("managed scope assignments did not persist")


def reconcile(admin, desired):
    # Initial realm creation is create-only. Changes use partial API writes so
    # registered users, credentials, keys, memberships and existing sessions
    # are never overwritten with an exported realm snapshot.
    existing = admin.request("GET", "/admin/realms")
    if not any(realm["realm"] == desired["realm"] for realm in existing):
        admin.request("POST", "/admin/realms", desired)
    flow = admin.flow("kaiba-passkey-only-v1")
    executions = admin.api("GET", "/authentication/flows/kaiba-passkey-only-v1/executions")
    if len(executions) != 1 or executions[0].get("providerId") != "webauthn-authenticator-passwordless" or executions[0]["requirement"] != "REQUIRED":
        raise Refuse("passkey-only authentication flow changed; refusing to broaden trust")
    enrollment_executions = admin.api("GET", "/authentication/flows/kaiba-owner-enrollment-v1/executions")
    expected_providers = ["auth-username-password-form", "conditional-user-role", "deny-access-authenticator"]
    actual_providers = [entry.get("providerId") for entry in enrollment_executions if entry.get("providerId")]
    if len(enrollment_executions) != 4 or [entry["level"] for entry in enrollment_executions] != [0, 0, 1, 1] or actual_providers != expected_providers or any(
        entry.get("requirement") != "REQUIRED" for entry in enrollment_executions if entry.get("providerId")
    ):
        raise Refuse("bounded owner enrollment flow changed")
    subflows = [entry for entry in enrollment_executions if entry.get("authenticationFlow")]
    if len(subflows) != 1 or subflows[0]["requirement"] != "CONDITIONAL" or not subflows[0].get("flowId"):
        raise Refuse("owner-only restriction must remain the conditional deny subflow")
    # The flow listing contains only top-level flows. Resolve the subflow by
    # its actual execution reference, then verify its identity and shape.
    subflow = admin.api("GET", "/authentication/flows/" + subflows[0]["flowId"])
    check_subset(subflow, {"alias": "kaiba-owner-enrollment-deny-v1", "topLevel": False,
        "builtIn": False, "providerId": "basic-flow"}, "enrollment deny subflow")
    conditions = [entry for entry in enrollment_executions if entry.get("providerId") == "conditional-user-role"]
    condition_config = admin.api("GET", "/authentication/config/" + conditions[0]["authenticationConfig"])
    check_subset(condition_config["config"], {"condUserRole": "kaiba-owner-enrolling", "negate": "true"}, "enrollment role restriction")
    realm_fields = {key: value for key, value in desired.items() if key not in {
        "authenticationFlows", "authenticatorConfig", "requiredActions", "clients", "groups", "roles",
        "defaultDefaultClientScopes", "defaultOptionalClientScopes",
    }}
    admin.api("PUT", value=realm_fields)
    check_subset(admin.api("GET"), realm_fields, "realm")
    scopes = admin.api("GET", "/client-scopes")
    # Realm GET/PUT omit these import-only fields; use their assignment API.
    reconcile_scopes(admin, "/default-default-client-scopes", desired["defaultDefaultClientScopes"], scopes)
    reconcile_scopes(admin, "/default-optional-client-scopes", desired["defaultOptionalClientScopes"], scopes)
    for expected in desired["clients"]:
        expected = dict(expected)
        selected_flow = flow if expected["clientId"] != "kaiba-owner-enrollment" else admin.flow("kaiba-owner-enrollment-v1")
        expected["authenticationFlowBindingOverrides"] = {"browser": selected_flow["id"]}
        client = admin.client(expected["clientId"])
        admin.api("PUT", "/clients/" + client["id"], expected)
        reconcile_scopes(admin, "/clients/" + client["id"] + "/default-client-scopes", expected["defaultClientScopes"], scopes)
        reconcile_scopes(admin, "/clients/" + client["id"] + "/optional-client-scopes", expected["optionalClientScopes"], scopes)
        # Keycloak stores mapper IDs and normalizes defaults, so compare their
        # security-relevant fields separately.
        actual = admin.client(expected["clientId"])
        check_subset(actual, {key: value for key, value in expected.items() if key != "protocolMappers"}, "client")
        for mapper in expected.get("protocolMappers", []):
            matches = [entry for entry in actual.get("protocolMappers", []) if entry["name"] == mapper["name"]]
            if len(matches) != 1:
                raise Refuse("managed groups mapper missing or ambiguous")
            check_subset(matches[0], mapper, "mapper")
    # Keycloak creates an admin-cli client in every realm. Its upstream
    # password grant is unnecessary here; master-realm local administration
    # uses a separate client and is unaffected.
    realm_admin_cli = admin.client("admin-cli")
    admin.api("PUT", "/clients/" + realm_admin_cli["id"], {"directAccessGrantsEnabled": False})
    if admin.client("admin-cli")["directAccessGrantsEnabled"]:
        raise Refuse("human realm admin-cli still permits password grants")
    required_action = desired["requiredActions"][0]
    action_path = "/authentication/required-actions/" + required_action["alias"]
    admin.api("PUT", action_path, required_action)
    check_subset(admin.api("GET", action_path), required_action, "passkey registration action")
    admin.group()
    print("Kaiba realm and SSH client policy verified; existing users and passkeys preserved.")


def state_path(directory):
    if os.geteuid() != 0:
        raise Refuse("owner enrollment management requires local root")
    directory = Path(directory)
    mode = directory.lstat()
    if not stat.S_ISDIR(mode.st_mode) or mode.st_uid != 0 or mode.st_mode & 0o077:
        raise Refuse("enrollment state directory must be root-owned mode 0700")
    return directory / "owner-enrollment.json"


def load_state(directory):
    path = state_path(directory)
    if not path.exists():
        return path, None
    return path, json.loads(private_read(path))


def pending_owner(admin, state):
    if state is None or not state.get("user_id") or state.get("phase") == "complete":
        raise Refuse("a recorded unfinished owner is required")
    user = admin.api("GET", "/users/" + state["user_id"])
    if user["username"] != state["owner"] or not user["enabled"]:
        raise Refuse("recorded owner identity changed or is disabled")
    groups = admin.api("GET", "/users/" + state["user_id"] + "/groups")
    if any(group["name"] == "kaiba-ssh-admin" for group in groups):
        raise Refuse("owner already has SSH authority; refusing a password reset")
    group = admin.group()
    if admin.api("GET", "/groups/" + group["id"] + "/members?max=1"):
        raise Refuse("an SSH administrator already exists; bootstrap is closed")
    return user


def open_enrollment(admin, path, state, desired):
    user = pending_owner(admin, state)
    admin.set_enrollment(False)
    state.update({"phase": "updating", "expires_at": int(time.time()) + 1800})
    private_write(path, json.dumps(state) + "\n")
    password = secrets.token_urlsafe(32)
    # This resets only the recorded unprivileged ceremony user's password.
    # Existing passkeys are never removed, including after an expired attempt.
    admin.api("PUT", "/users/" + state["user_id"] + "/reset-password", {
        "type": "password", "temporary": False, "value": password,
    })
    required = list(user.get("requiredActions", []))
    if "webauthn-register-passwordless" not in required:
        required.append("webauthn-register-passwordless")
    admin.api("PUT", "/users/" + state["user_id"], {"requiredActions": required})
    admin.api("POST", "/users/" + state["user_id"] + "/role-mappings/realm", [admin.owner_role()])
    private_write(path.parent / "owner-enrollment-password", password + "\n")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    # The enrollment callback never exchanges a code. Its only purpose is the
    # passkey required action; account-console authentication afterward uses
    # the normal passkey-only realm flow.
    query = urllib.parse.urlencode({
        "client_id": "kaiba-owner-enrollment", "response_type": "code", "scope": "openid",
        "redirect_uri": desired["clients"][1]["redirectUris"][0],
        "code_challenge_method": "S256", "code_challenge": challenge,
        "login_hint": state["owner"],
    })
    origin = "https://" + desired["webAuthnPolicyPasswordlessRpId"]
    url = origin + "/realms/" + desired["realm"] + "/protocol/openid-connect/auth?" + query
    private_write(path.parent / "owner-enrollment-url", url + "\n")
    state["phase"] = "enrolling"
    private_write(path, json.dumps(state) + "\n")
    admin.set_enrollment(True)
    print("Owner enrollment is open for 30 minutes (expiry checked every minute).")
    print("Use your existing administrator SSH session to read owner-enrollment-url and owner-enrollment-password in " + str(path.parent))
    print("Register a passkey, then add a second in the account console. SSH remains denied until enroll-finalize.")


def enrollment_start(admin, args, desired):
    path, state = load_state(args.state_directory)
    if state is not None:
        raise Refuse("an owner ceremony already exists; use enroll-status, enroll-resume or enroll-finalize")
    if not args.owner or not re.fullmatch(r"[a-z][a-z0-9._-]{0,63}", args.owner):
        raise Refuse("enroll-start requires --owner with a simple lowercase account name")
    if admin.api("GET", "/users?exact=true&username=" + args.owner):
        raise Refuse("owner already exists; refusing to reset a user's credentials")
    group = admin.group()
    if admin.api("GET", "/groups/" + group["id"] + "/members?max=1"):
        raise Refuse("initial owner is already enrolled; refusing another bootstrap ceremony")
    # Durable intent precedes user creation. If the response is lost, stop for
    # identity reconciliation rather than resetting an unrecorded account.
    state = {"owner": args.owner, "phase": "creating", "expires_at": int(time.time()) + 1800}
    private_write(path, json.dumps(state) + "\n")
    admin.api("POST", "/users", {
        "username": args.owner, "enabled": True,
        "firstName": args.owner, "lastName": "Kaiba operator",
        "requiredActions": ["webauthn-register-passwordless"],
    })
    users = admin.api("GET", "/users?exact=true&username=" + args.owner)
    if len(users) != 1:
        raise Refuse("created owner cannot be uniquely reconciled")
    state["user_id"] = users[0]["id"]
    private_write(path, json.dumps(state) + "\n")
    open_enrollment(admin, path, state, desired)


def enrollment_resume(admin, args, desired):
    path, state = load_state(args.state_directory)
    pending_owner(admin, state)
    open_enrollment(admin, path, state, desired)


def enrollment_status(admin, args):
    _, state = load_state(args.state_directory)
    if state is None:
        print(json.dumps({"phase": "not-started"}))
        return
    public = {"phase": state["phase"], "expires_at": state["expires_at"]}
    if state.get("user_id"):
        user = admin.api("GET", "/users/" + state["user_id"])
        if user["username"] != state["owner"]:
            raise Refuse("recorded owner identity differs")
        credentials = admin.api("GET", "/users/" + state["user_id"] + "/credentials")
        public.update({"subject": state["user_id"], "principal": "kaiba:person:" + state["user_id"],
            "passkey_count": sum(entry["type"] == "webauthn-passwordless" for entry in credentials)})
    print(json.dumps(public, sort_keys=True))


def delete_passwords(admin, user_id):
    base = "/users/" + user_id + "/credentials"
    for credential in admin.api("GET", base):
        if credential["type"] == "password":
            admin.api("DELETE", base + "/" + credential["id"])
    if any(entry["type"] == "password" for entry in admin.api("GET", base)):
        raise Refuse("owner password removal was not confirmed")


def enrollment_finalize(admin, args):
    path, state = load_state(args.state_directory)
    if state is None or not state.get("user_id"):
        raise Refuse("no complete owner creation record; reconcile locally before continuing")
    user_id = state["user_id"]
    user = admin.api("GET", "/users/" + user_id)
    if user["username"] != state["owner"] or not user["enabled"]:
        raise Refuse("recorded owner identity changed or is disabled")
    credentials = admin.api("GET", "/users/" + user_id + "/credentials")
    passkeys = [entry for entry in credentials if entry["type"] == "webauthn-passwordless"]
    if len({entry["id"] for entry in passkeys}) < 2:
        raise Refuse("two distinct registered passkey credentials are required")
    # Disable bootstrap before granting authority, including when resuming an
    # interrupted finalization. Root can finish after expiry using retained keys.
    admin.set_enrollment(False)
    delete_passwords(admin, user_id)
    admin.api("DELETE", "/users/" + user_id + "/role-mappings/realm", [admin.owner_role()])
    admin.api("PUT", "/users/" + user_id + "/groups/" + admin.group()["id"], {})
    groups = admin.api("GET", "/users/" + user_id + "/groups")
    if not any(group["name"] == "kaiba-ssh-admin" for group in groups):
        raise Refuse("SSH administrator membership was not confirmed")
    state["phase"] = "complete"
    private_write(path, json.dumps(state) + "\n")
    (path.parent / "owner-enrollment-password").unlink(missing_ok=True)
    (path.parent / "owner-enrollment-url").unlink(missing_ok=True)
    print("Owner finalized: two passkeys, no password, enrollment disabled, SSH administrator group assigned.")


def expire_enrollment(admin, args):
    path, state = load_state(args.state_directory)
    if state is None or state["phase"] in {"complete", "expired"} or state["expires_at"] > time.time():
        return
    admin.set_enrollment(False)
    if state.get("user_id"):
        delete_passwords(admin, state["user_id"])
        admin.api("DELETE", "/users/" + state["user_id"] + "/role-mappings/realm", [admin.owner_role()])
    state["phase"] = "expired"
    private_write(path, json.dumps(state) + "\n")
    (path.parent / "owner-enrollment-password").unlink(missing_ok=True)
    (path.parent / "owner-enrollment-url").unlink(missing_ok=True)
    print("Owner enrollment expired; bootstrap client and password disabled, SSH authority unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-file")
    parser.add_argument("--state-directory", required=True)
    parser.add_argument("command", choices=["reconcile", "enroll-start", "enroll-resume", "enroll-status", "enroll-finalize", "expire-enrollment"])
    parser.add_argument("--owner")
    args = parser.parse_args()
    # Serialize explicit start/finalize and the expiry timer across API calls.
    # Never let expiry race a finalization and leave bootstrap enabled.
    enrollment_lock = None
    if args.command != "reconcile":
        lock_path = state_path(args.state_directory).with_suffix(".lock")
        enrollment_lock = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(enrollment_lock, fcntl.LOCK_EX)
    desired = json.loads(Path(args.config).read_text())
    if args.command == "expire-enrollment":
        _, state = load_state(args.state_directory)
        if state is None or state["phase"] in {"complete", "expired"} or state["expires_at"] > time.time():
            return
    password_file = args.password_file or os.path.join(os.environ.get("CREDENTIALS_DIRECTORY", ""), "admin-password")
    admin = Admin(args.url, args.username, private_read(password_file).rstrip("\n"), desired["realm"])
    if args.command == "reconcile":
        reconcile(admin, desired)
    elif args.command == "enroll-start":
        enrollment_start(admin, args, desired)
    elif args.command == "enroll-resume":
        enrollment_resume(admin, args, desired)
    elif args.command == "enroll-status":
        enrollment_status(admin, args)
    elif args.command == "enroll-finalize":
        enrollment_finalize(admin, args)
    else:
        expire_enrollment(admin, args)


if __name__ == "__main__":
    try:
        main()
    except (Refuse, OSError, KeyError, ValueError) as error:
        print("kaiba-human-identity: " + str(error), file=sys.stderr)
        sys.exit(1)
