#!/usr/bin/env python3
"""Bootstrap one admitted OIDC subject; preserve realm, users and passkeys."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from keycloak_admin import Admin, Refuse, private_read, private_write
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
from forgejo_migrate import Forge


def checked(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise Refuse("Forgejo administration command failed; credential-bearing output suppressed")
    return result.stdout


def validate_auth_source(source, client_name, secret, issuer, subject):
    expected = {"Provider": "openidConnect", "ClientID": client_name, "ClientSecret": secret,
        "OpenIDConnectAutoDiscoveryURL": issuer + "/.well-known/openid-configuration",
        "RequiredClaimName": "sub", "RequiredClaimValue": subject,
        "SkipLocalTwoFA": True, "Scopes": ["openid", "profile", "email"]}
    if any(source.get(field) != value for field, value in expected.items()):
        raise Refuse("existing Forgejo authentication policy differs; explicit update required")
    if any(source.get(field) for field in ("GroupClaimName", "AdminGroup", "GroupTeamMap",
            "QuotaGroupClaimName", "QuotaGroupMap", "AttributeSSHPublicKey", "AllowUsernameChange")):
        raise Refuse("existing Forgejo authentication source has additional identity mappings")


def validate_owner_binding(users, username, source_id, subject):
    matches = [user for user in users if user.get("login") == username]
    if len(matches) != 1 or matches[0].get("source_id") != source_id or matches[0].get("login_name") != subject:
        raise Refuse("existing Forgejo owner identity differs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forgejo", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--owner-subject", required=True)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--admin-url", required=True)
    args = parser.parse_args()
    state = Path("/var/lib/kaiba-forgejo-admin")
    password = private_read(Path(os.environ["CREDENTIALS_DIRECTORY"]) / "admin-password").strip()
    keycloak = Admin(args.admin_url, "kaiba-bootstrap-admin", password, "kaiba")
    client_name = "kaiba-forgejo"
    redirect = f"https://{args.domain}/user/oauth2/kaiba/callback"
    clients = keycloak.api("GET", "/clients?clientId=" + client_name)
    exact = [client for client in clients if client["clientId"] == client_name]
    if len(exact) > 1:
        raise Refuse("duplicate Forgejo OIDC clients")
    desired = {"clientId": client_name, "protocol": "openid-connect", "publicClient": False,
        "enabled": True, "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False, "redirectUris": [redirect], "webOrigins": [f"https://{args.domain}"],
        "attributes": {"pkce.code.challenge.method": "S256"}}
    if not exact:
        keycloak.api("POST", "/clients", desired)
        exact = keycloak.api("GET", "/clients?clientId=" + client_name)
    if len(exact) != 1:
        raise Refuse("OIDC client creation readback failed")
    client = keycloak.api("GET", "/clients/" + exact[0]["id"])
    for field, value in desired.items():
        if field == "attributes":
            if any(client.get(field, {}).get(k) != v for k, v in value.items()):
                raise Refuse("existing OIDC client policy differs")
        elif client.get(field) != value:
            raise Refuse("existing OIDC client policy differs: " + field)
    secret = keycloak.api("GET", "/clients/" + client["id"] + "/client-secret")["value"]
    secret_path = state / "oidc-client-secret"
    if not secret_path.exists():
        private_write(secret_path, secret + "\n")
    elif private_read(secret_path).strip() != secret:
        raise Refuse("OIDC secret changed; explicit rotation required")
    base = ["runuser", "-u", "forgejo", "--", args.forgejo,
        "--work-path", "/var/lib/forgejo", "--config", "/var/lib/forgejo/custom/conf/app.ini", "admin"]
    auths = checked(base + ["auth", "list"])
    if not any("kaiba" in line.split() for line in auths.splitlines()[1:]):
        checked(base + ["auth", "add-oauth", "--name", "kaiba", "--provider", "openidConnect",
            "--key", client_name, "--secret", secret, "--auto-discover-url", args.issuer + "/.well-known/openid-configuration",
            "--scopes", "openid", "--scopes", "profile", "--scopes", "email",
            "--required-claim-name", "sub", "--required-claim-value", args.owner_subject,
            "--skip-local-2fa"])
    # Re-read the persisted authentication policy instead of trusting its name.
    source = json.loads(checked(["runuser", "-u", "postgres", "--", "psql", "-d", "forgejo", "-tAc",
        "SELECT cfg FROM login_source WHERE name = 'kaiba'"]))
    validate_auth_source(source, client_name, secret, args.issuer, args.owner_subject)
    # Never silently rotate an existing administrator or mint repeated tokens.
    users = checked(base + ["user", "list"])
    if not any("forge-recovery" in line.split() for line in users.splitlines()[1:]):
        recovery_path = state / "recovery-password"
        if not recovery_path.exists():
            private_write(recovery_path, secrets.token_urlsafe(48) + "\n")
        recovery_password = private_read(recovery_path).strip()
        checked(base + ["user", "create", "--username", "forge-recovery", "--email", "forge-recovery@pseudo.design",
            "--password", recovery_password, "--admin", "--must-change-password=false"])
    token_path = state / "migration-token"
    if not token_path.exists():
        token = checked(base + ["user", "generate-access-token", "--username", "forge-recovery",
            "--token-name", "migration-bootstrap", "--scopes", "all", "--raw"]).strip()
        if not token or any(c.isspace() for c in token):
            raise Refuse("invalid migration token output")
        private_write(token_path, token + "\n")
    owner = keycloak.api("GET", "/users/" + args.owner_subject)
    if owner.get("id") != args.owner_subject or owner.get("enabled") is not True:
        raise Refuse("admitted owner missing or disabled")
    source_id = int(checked(["runuser", "-u", "postgres", "--", "psql", "-d", "forgejo", "-tAc",
        "SELECT id FROM login_source WHERE name = 'kaiba'"]).strip())
    forge = Forge("http://127.0.0.1:3010", private_read(token_path).strip())
    username = owner["username"]
    existing = forge.request("GET", "/users/" + username)
    if existing is None:
        forge.request("POST", "/admin/users", {"username": username, "email": owner["email"],
            "source_id": source_id, "login_name": args.owner_subject, "must_change_password": False})
    # The administrator endpoint includes external login bindings. Never claim
    # an existing local account based only on its username or email address.
    users = forge.request("GET", "/admin/users?limit=50")
    validate_owner_binding(users, username, source_id, args.owner_subject)
    forge.request("PATCH", "/admin/users/" + username, {"admin": True, "source_id": source_id, "login_name": args.owner_subject})
    print(json.dumps({"oidc_client": client_name, "owner_admission": "subject", "owner": username, "configured": True}))


if __name__ == "__main__":
    try:
        main()
    except (Refuse, RuntimeError, OSError, KeyError, subprocess.SubprocessError):
        print("Forgejo SSO bootstrap failed; secrets suppressed", file=sys.stderr)
        raise SystemExit(1)
