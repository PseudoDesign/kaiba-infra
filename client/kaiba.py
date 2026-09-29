"""Human-only SSH login. Private keys stay in the caller's local SSH agent."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import ssl
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener
import uuid


class LoginError(Exception):
    pass


def run(args, *, input=None, interactive=False, env=None):
    result = subprocess.run(args, input=input, text=True, env=env,
                            capture_output=not interactive, check=False)
    if result.returncode:
        # Do not echo subprocess output: authentication errors can contain data
        # from a provider. The interactive login renders its own browser prompt.
        raise LoginError(f"{args[0]} failed (exit {result.returncode})")
    return result.stdout or ""


def https_url(value):
    if not isinstance(value, str):
        raise LoginError("Expected an HTTPS URL in the public configuration")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or any(c.isspace() for c in value)):
        raise LoginError("Expected an HTTPS URL without credentials, query or fragment")
    return value.rstrip("/")


def load_config(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid())
            or info.st_mode & 0o022):
        raise LoginError("Public login configuration must be an owner/root-controlled regular file")
    config = json.loads(path.read_text())
    expected = {"caURL", "rootFingerprint", "sshUserCAFingerprint", "issuer", "clientID", "principal"}
    if not isinstance(config, dict) or set(config) != expected:
        raise LoginError("Login configuration must contain exactly: " + ", ".join(sorted(expected)))
    config["caURL"] = https_url(config["caURL"])
    config["issuer"] = https_url(config["issuer"])
    if not re.fullmatch(r"[0-9a-fA-F]{64}", config["rootFingerprint"]):
        raise LoginError("rootFingerprint must be the reviewed SHA256 root certificate fingerprint")
    if not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", config["sshUserCAFingerprint"]):
        raise LoginError("sshUserCAFingerprint must be the reviewed OpenSSH SHA256 fingerprint")
    if config["clientID"] != "kaiba-ssh":
        raise LoginError("This client requires the public kaiba-ssh OIDC client")
    if not re.fullmatch(r"kaiba:person:[A-Za-z0-9._-]+", config["principal"]):
        raise LoginError("principal must bind the authorized person's immutable OIDC subject")
    return config


def agent_identity():
    # Human credentials belong on the operator workstation, not in an SSH
    # session, an agent workspace, or a socket forwarded to another machine.
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
        raise LoginError("Run kaiba on your own workstation, outside a remote SSH session")
    value = os.environ.get("SSH_AUTH_SOCK")
    if not value:
        raise LoginError("Start your local SSH agent before using kaiba")
    path = Path(value).resolve(strict=True)
    info = path.stat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise LoginError("SSH_AUTH_SOCK must be a socket owned by your local account")
    return {"path": str(path), "device": info.st_dev, "inode": info.st_ino}


def agent_keys():
    result = subprocess.run(["ssh-add", "-L"], text=True, capture_output=True, check=False)
    if result.returncode == 1:
        return []
    if result.returncode:
        raise LoginError("Cannot read identities from the local SSH agent")
    return [line for line in result.stdout.splitlines() if line]


def owned_keys(comment):
    return [line for line in agent_keys() if line.split(" ", 2)[-1] == comment]


def remove_keys(keys):
    for key in keys:
        # -d removes only the supplied public certificate. Never use -D or
        # step ssh logout, which can remove identities this tool did not add.
        run(["ssh-add", "-d", "-"], input=key + "\n")


@contextmanager
def state_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise LoginError("Kaiba state directory must be owned by you with mode 0700")
    flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
    with os.fdopen(os.open(path / "lock", flags, 0o600), "r+") as lock:
        lock_info = os.fstat(lock.fileno())
        if lock_info.st_uid != os.getuid() or lock_info.st_mode & 0o077 or lock_info.st_nlink != 1:
            raise LoginError("Kaiba state lock must be owner-only with one link")
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield path / "session.json"


def write_atomic(path, content):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def write_state(path, state):
    write_atomic(path, json.dumps(state) + "\n")


def old_socket_stale(recorded):
    if (not isinstance(recorded, dict) or set(recorded) != {"path", "device", "inode"}
            or not isinstance(recorded["path"], str) or not Path(recorded["path"]).is_absolute()
            or type(recorded["device"]) is not int or type(recorded["inode"]) is not int):
        raise LoginError("Invalid recorded SSH agent identity")
    try:
        info = Path(recorded["path"]).lstat()
    except FileNotFoundError:
        return True
    # Other lookup failures (e.g. permission denied) do not establish that the
    # agent disappeared. A still-live original socket must not be forgotten.
    return (not stat.S_ISSOCK(info.st_mode)
            or info.st_dev != recorded["device"] or info.st_ino != recorded["inode"])


def read_state(path, agent, *, cleanup_stale=False):
    if not path.exists():
        return None
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise LoginError("Kaiba session record must be an owner-only regular file")
    state = json.loads(path.read_text())
    if not isinstance(state, dict):
        raise LoginError("Invalid Kaiba session record")
    if not re.fullmatch(r"kaiba-human:[0-9a-f]{32}", state.get("comment", "")):
        raise LoginError("Invalid Kaiba session record")
    if state.get("agent") != agent:
        if cleanup_stale and old_socket_stale(state.get("agent")):
            path.with_name("certificate.pub").unlink(missing_ok=True)
            path.unlink()
            print("Previous SSH agent socket is gone or replaced; cleared only Kaiba's public login record. Existing sessions are unchanged.", file=sys.stderr)
            return None
        raise LoginError("This login belongs to a different SSH agent; use its original agent to log out")
    return state


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LoginError("The CA must not redirect provisioner discovery")


def verify_provisioner(config, bundle):
    context = ssl.create_default_context(cafile=str(bundle))
    opener = build_opener(HTTPSHandler(context=context), NoRedirect())
    request = Request(config["caURL"] + "/provisioners", headers={"Accept": "application/json"})
    with opener.open(request, timeout=20) as response:
        data = response.read(65537)
    if len(data) > 65536:
        raise LoginError("CA provisioner response is too large")
    data = json.loads(data)
    if not isinstance(data, dict) or data.get("nextCursor"):
        raise LoginError("CA provisioner discovery was incomplete")
    matching = [p for p in data.get("provisioners", []) if p.get("name") == "kaiba-human"]
    if len(matching) != 1:
        raise LoginError("CA must expose exactly one kaiba-human provisioner")
    provisioner = matching[0]
    if (provisioner.get("type") != "OIDC"
            or provisioner.get("clientID") != config["clientID"]
            or provisioner.get("configurationEndpoint") != config["issuer"] + "/.well-known/openid-configuration"
            or provisioner.get("listenAddress") != "127.0.0.1:8400"
            or provisioner.get("clientSecret")):
        raise LoginError("CA OIDC provisioner does not match the pinned public login configuration")


def inspect_certificate(key, config, *, now=None, active=True):
    # OpenSSH verifies the certificate signature when parsing it. step's JSON
    # inspector supplies convenient fields but does not verify that signature.
    run(["ssh-keygen", "-L", "-f", "/dev/stdin"], input=key + "\n")
    value = json.loads(run(["step", "ssh", "inspect", "--format", "json"], input=key + "\n"))
    now = now or datetime.now(timezone.utc)
    before = datetime.fromisoformat(value["ValidBefore"].replace("Z", "+00:00"))
    after = datetime.fromisoformat(value["ValidAfter"].replace("Z", "+00:00"))
    if (value.get("Type") != "user" or value.get("Principals") != [config["principal"]]
            or value.get("SigningKeyFingerprint") != config["sshUserCAFingerprint"]
            or value.get("KeyID") != config["issuer"] + "#" + config["principal"].removeprefix("kaiba:person:")
            or before.tzinfo is None or after.tzinfo is None
            or (before - after).total_seconds() > 8 * 3600 + 120
            or after >= before):
        raise LoginError("Issued SSH certificate does not match the pinned identity, CA or lifetime")
    if active and not after <= now < before:
        raise LoginError("SSH certificate is not currently valid; log out and log in again")
    return {"principal": config["principal"], "expires": before.isoformat(), "active": after <= now < before}


def login(config, state_path, agent):
    if read_state(state_path, agent, cleanup_stale=True):
        raise LoginError("A Kaiba login is already recorded; use kaiba status or kaiba logout first")
    comment = "kaiba-human:" + uuid.uuid4().hex
    # Persist the exact ownership marker first, so an interrupted browser login
    # can be cleaned up without touching other keys in the user's agent.
    state = {"agent": agent, "comment": comment}
    write_state(state_path, state)
    try:
        with tempfile.TemporaryDirectory(prefix="login-", dir=state_path.parent) as temporary:
            directory = Path(temporary)
            env = {**os.environ, "STEPPATH": str(directory / "step")}
            root = directory / "root.pem"
            run(["step", "ca", "root", str(root), "--ca-url", config["caURL"],
                 "--fingerprint", config["rootFingerprint"]], env=env)
            # nginx has a public ACME certificate; the CA's fingerprint-pinned
            # root is separate from HTTPS ingress. Trust both roots explicitly.
            system_roots = ssl.get_default_verify_paths().cafile
            if not system_roots:
                raise LoginError("A system TLS trust bundle is required")
            bundle = directory / "trust.pem"
            bundle.write_bytes(Path(system_roots).read_bytes() + b"\n" + root.read_bytes())
            verify_provisioner(config, bundle)
            # Let the CA apply its bounded default duration. step fixes the
            # start before browser authentication; a relative --not-after
            # would be evaluated later and inflate the requested lifetime.
            run(["step", "ssh", "login", "--force", "--comment", comment,
                 "--provisioner", "kaiba-human",
                 "--ca-url", config["caURL"], "--root", str(bundle)], interactive=True, env=env)
            if agent_identity() != agent:
                raise LoginError("The SSH agent changed during login; start a new login in your local agent")
            keys = owned_keys(comment)
            if len(keys) != 1:
                raise LoginError("Login did not add exactly one Kaiba certificate to your SSH agent")
            result = inspect_certificate(keys[0], config)
            state["certificate"] = keys[0]
            write_state(state_path, state)
            certificate_path = state_path.with_name("certificate.pub")
            write_atomic(certificate_path, keys[0] + "\n")
            return result | {"certificateFile": str(certificate_path)}
    except BaseException:
        # Keep the marker if cleanup fails so logout can be retried.
        remove_keys(owned_keys(comment))
        state_path.with_name("certificate.pub").unlink(missing_ok=True)
        state_path.unlink(missing_ok=True)
        raise


def status(config, state_path, agent):
    state = read_state(state_path, agent)
    if not state:
        return {"active": False, "reason": "No Kaiba login recorded"}
    keys = owned_keys(state["comment"])
    if not keys:
        return {"active": False, "reason": "Certificate is absent from this SSH agent"}
    if len(keys) != 1 or state.get("certificate") != keys[0]:
        raise LoginError("Incomplete or changed login; use kaiba logout before logging in again")
    return inspect_certificate(keys[0], config, active=False) | {
        "certificateFile": str(state_path.with_name("certificate.pub"))}


def logout(state_path, agent):
    state = read_state(state_path, agent, cleanup_stale=True)
    if state:
        keys = owned_keys(state["comment"])
        if state.get("certificate") and any(key != state["certificate"] for key in keys):
            raise LoginError("Recorded SSH certificate changed; refusing to remove another identity")
        remove_keys(keys)
        state_path.with_name("certificate.pub").unlink(missing_ok=True)
        state_path.unlink()
    return {"active": False, "reason": "Kaiba login cleared; existing SSH connections and browser sessions are unchanged"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kaiba", description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kaiba/login.json")
    parser.add_argument("command", choices=["login", "status", "logout"])
    args = parser.parse_args(argv)
    try:
        agent = agent_identity()
        state_dir = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "kaiba"
        with state_directory(state_dir) as state_path:
            if args.command == "logout":
                result = logout(state_path, agent)
            else:
                config = load_config(args.config)
                result = globals()[args.command](config, state_path, agent)
        print(json.dumps(result, indent=2))
        return 0
    except (LoginError, OSError, ValueError, KeyError, TypeError) as error:
        # Values in malformed configuration/provider JSON are not echoed.
        print("kaiba: " + (str(error) if isinstance(error, LoginError) else "Login state or configuration could not be verified"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
