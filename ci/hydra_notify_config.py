#!/usr/bin/env python3
"""Render the notifier's private configuration from a systemd credential."""

import argparse
import json
import os
from pathlib import Path
import re


def render(token, inventory):
    token = token.rstrip("\n")
    if not re.fullmatch(r"[A-Za-z0-9_]+", token):
        raise ValueError("GitHub credential must be a single token")
    jobs = [("kaiba-infra", "aarch64-linux.selector")]
    for attribute in inventory["jobs"]:
        if not re.fullmatch(r"checks\.aarch64-linux\.[a-z0-9-]+", attribute):
            raise ValueError("invalid provisioning inventory attribute")
        jobs.append(("kaiba-provisioning", attribute.removeprefix("checks.")))
    if len(set(jobs)) != len(jobs):
        raise ValueError("duplicate notification job")
    lines = ["Include /var/lib/hydra/hydra.conf"]
    for project, job in jobs:
        lines.extend([
            "<githubstatus>",
            f"  jobs = {re.escape(project + ':main:' + job)}",
            f"  context = ci/hydra/{project}/{job}",
            "  inputs = src",
            f"  authorization = Bearer {token}",
            "</githubstatus>",
        ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    credential = Path(os.environ["CREDENTIALS_DIRECTORY"]) / "github-token"
    inventory = json.loads(Path(__file__).with_name("provisioning-arm64.json").read_text())
    config = render(credential.read_text(), inventory)
    # RuntimeDirectory is private and owned by the notifier, outside the store
    # and outside Hydra's backed-up state directory.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(config)


if __name__ == "__main__":
    main()
