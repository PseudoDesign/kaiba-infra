#!/usr/bin/env python3
"""Queue successful main builds and publish their build closures to Cachix."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


STORE_PATH = re.compile(r"/nix/store/[0-9a-z]{32}-[A-Za-z0-9+._?=-]+")


def validate(payload):
    if (payload.get("project"), payload.get("jobset")) != ("kaiba-provisioning", "main"):
        raise ValueError("only provisioning main builds may be published")
    inventory = json.loads(Path(__file__).with_name("provisioning-arm64.json").read_text())
    jobs = {item.removeprefix("checks.") for item in inventory["jobs"]}
    if payload.get("job") not in jobs or payload.get("system") != "aarch64-linux":
        raise ValueError("build is outside the qualified ARM64 inventory")
    if type(payload.get("build")) is not int or payload["build"] <= 0:
        raise ValueError("invalid build ID")
    drv = payload.get("drvPath", "")
    if not isinstance(drv, str) or not STORE_PATH.fullmatch(drv) or not drv.endswith(".drv"):
        raise ValueError("invalid derivation path")
    if payload.get("finished") != 1 or payload.get("buildStatus") != 0:
        raise ValueError("only successful finished builds may be published")
    outputs = payload.get("outputs")
    if not isinstance(outputs, list) or not outputs or any(
        not isinstance(item, dict) or not isinstance(item.get("path"), str)
        or not STORE_PATH.fullmatch(item["path"]) for item in outputs
    ):
        raise ValueError("invalid build outputs")
    return payload


def enqueue(payload, spool):
    # Failed builds are normal notifications, not publication requests.
    if payload.get("finished") != 1 or payload.get("buildStatus") != 0:
        return
    validate(payload)
    with tempfile.NamedTemporaryFile(mode="w", dir=spool, prefix=".pending-", delete=False) as output:
        temporary = Path(output.name)
        json.dump(payload, output)
    try:
        temporary.replace(spool / f'{payload["build"]}.json')
    finally:
        temporary.unlink(missing_ok=True)


def publish(spool, token_file, cache, run=subprocess.run):
    token = token_file.read_text().strip()
    if not token or any(character.isspace() for character in token):
        raise ValueError("Cachix credential must be a single token")
    environment = os.environ | {"CACHIX_AUTH_TOKEN": token}
    failures = 0
    for pending in sorted(spool.glob("*.json")):
        try:
            payload = validate(json.loads(pending.read_text()))
            # Test outputs can be empty. Include valid build-time outputs too,
            # so the cache also receives new kernels, compilers and images.
            closure = run(["nix-store", "--query", "--requisites", "--include-outputs",
                           payload["drvPath"]], check=True, capture_output=True, text=True)
            paths = set(closure.stdout.splitlines()) | {item["path"] for item in payload["outputs"]}
            if not paths or any(not STORE_PATH.fullmatch(path) for path in paths):
                raise ValueError("invalid closure path")
            run(["cachix", "push", cache], input="\n".join(sorted(paths)) + "\n",
                text=True, env=environment, check=True)
            pending.unlink()
            print(f'Published Hydra build {payload["build"]}', flush=True)
        except (OSError, ValueError, subprocess.CalledProcessError):
            # Do not log a subprocess environment or credential-bearing output.
            print(f"Publication pending for {pending.name}; will retry", flush=True)
            failures += 1
    return int(failures > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("enqueue", "publish"))
    parser.add_argument("--spool", type=Path, default=Path("/var/lib/kaiba-hydra-publish"))
    parser.add_argument("--cache", default="kaiba-provisioning")
    args = parser.parse_args()
    if args.command == "enqueue":
        enqueue(json.loads(Path(os.environ["HYDRA_JSON"]).read_text()), args.spool)
        return 0
    credential = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "cachix-token"
    return publish(args.spool, credential, args.cache)


if __name__ == "__main__":
    raise SystemExit(main())
