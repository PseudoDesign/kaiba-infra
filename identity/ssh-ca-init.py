"""Explicit, never-overwrite initialization of the Kaiba human SSH CA.

Run only during the owner-approved host ceremony. All private material is created
on the target host, never by Nix builds. A partial initialization is retained for
inspection, not silently replaced with new trust.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys


def initialize(step, state_dir):
    if os.geteuid() != 0:
        raise SystemExit("Run this ceremony as root on the intended CA host.")
    state = Path(state_dir)
    if not state.is_absolute():
        raise SystemExit("CA state directory must be absolute.")
    parent = state.parent
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        raise SystemExit("CA state parent must be a real, root-owned directory without group/world write access.")
    os.umask(0o077)
    # mkdir deliberately fails for every existing path, including an empty
    # directory or symlink. There is no --force, restore, or repair mode.
    try:
        state.mkdir(mode=0o700)
    except FileExistsError:
        raise SystemExit("Refusing existing CA state: initialization never replaces trust.") from None
    offline = state / "offline-root"
    offline.mkdir(mode=0o700)
    (state / "password").write_text(secrets.token_urlsafe(48) + "\n")
    (offline / "password").write_text(secrets.token_urlsafe(48) + "\n")

    def run(*args):
        return subprocess.run([step, *map(str, args)], check=True, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout

    try:
        run("certificate", "create", "Kaiba Human SSH Transport Root", state / "root_ca.crt",
            offline / "root_ca_key", "--profile", "root-ca", "--not-after", "87600h",
            "--password-file", offline / "password")
        run("certificate", "create", "Kaiba Human SSH Transport Intermediate", state / "intermediate_ca.crt",
            state / "intermediate_ca_key", "--profile", "intermediate-ca", "--not-after", "43800h",
            "--ca", state / "root_ca.crt", "--ca-key", offline / "root_ca_key",
            "--ca-password-file", offline / "password", "--password-file", state / "password")
        run("crypto", "keypair", state / "ssh_user_ca.pem", state / "ssh_user_ca_key",
            "--kty", "OKP", "--curve", "Ed25519", "--password-file", state / "password")
        public_key = run("crypto", "key", "format", state / "ssh_user_ca.pem", "--ssh").strip()
        (state / "ssh_user_ca.pub").write_text(public_key + "\n")
        fingerprint = run("certificate", "fingerprint", state / "root_ca.crt").strip()
        public = {"rootFingerprint": fingerprint, "sshUserCA": public_key}
        (state / "public-trust.json").write_text(json.dumps(public, indent=2) + "\n")
        (state / "initialized").write_text("kaiba-human-ssh-ca-v1\n")
    except subprocess.CalledProcessError as error:
        # Never echo subprocess output that could contain private key material.
        raise SystemExit("CA initialization failed; partial state retained. Inspect it before any recovery.") from error
    print(json.dumps(public, indent=2))
    print("CA initialized. Back up this entire directory with authenticated encryption to owner-controlled storage.", file=sys.stderr)
    print("After verifying recovery, remove offline-root/ from the online host; never copy its contents into Git or Nix.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", required=True)
    parser.add_argument("--state-dir", default="/var/lib/kaiba-ssh-ca")
    args = parser.parse_args()
    initialize(args.step, args.state_dir)


if __name__ == "__main__":
    main()
