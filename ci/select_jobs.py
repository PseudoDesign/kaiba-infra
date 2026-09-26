#!/usr/bin/env python3
"""Compare complete base/head derivation manifests for inventoried Nix jobs."""

import argparse
import json
import re
import sys
from pathlib import PurePosixPath

STORE_DRV = re.compile(r"^/nix/store/[a-z0-9]{32}-[^/]+\.drv$")
FULL_PATHS = {"flake.nix", "flake.lock", "ci/select_jobs.py", "ci/provisioning-arm64.json"}
FULL_PREFIXES = ("nix/", "lib/", "modules/", "tests/lib/", ".github/workflows/")


def parse_inventory(data):
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("inventory must contain a jobs array")
    jobs = data["jobs"]
    if not jobs or any(not isinstance(job, str) or not job.startswith("checks.") for job in jobs):
        raise ValueError("inventory jobs must be nonempty check attribute names")
    if len(jobs) != len(set(jobs)):
        raise ValueError("inventory contains duplicate jobs")
    return jobs


def valid_manifest(manifest, jobs):
    return (isinstance(manifest, dict) and set(manifest) == set(jobs)
            and all(isinstance(value, str) and STORE_DRV.fullmatch(value)
                    for value in manifest.values()))


def select(jobs, base, head, changed_paths=(), evaluation_failed=False):
    """Return full selection on uncertainty; otherwise return changed drv jobs."""
    reasons = []
    if evaluation_failed or not valid_manifest(base, jobs) or not valid_manifest(head, jobs):
        reasons.append("incomplete-or-failed-evaluation")
    for raw_path in changed_paths:
        # Git path names are repo-relative POSIX paths. Malformed input is unsafe.
        if (not isinstance(raw_path, str) or not raw_path or raw_path.startswith("/")
                or "\\" in raw_path or any(p in (".", "..") for p in raw_path.split("/"))):
            reasons.append("invalid-changed-path")
            continue
        path = PurePosixPath(raw_path).as_posix()
        if path in FULL_PATHS or path.startswith(FULL_PREFIXES):
            reasons.append("shared-or-ci-change:" + path)
    if reasons:
        return {"mode": "all", "jobs": jobs, "reasons": sorted(set(reasons))}
    changed = [job for job in jobs if base[job] != head[job]]
    return {"mode": "changed", "jobs": changed, "reasons": ["derivation-changed:" + job for job in changed]}


def load_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--evaluation-failed", action="store_true")
    args = parser.parse_args(argv)
    try:
        jobs = parse_inventory(load_json(args.inventory))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        # There is no safe job universe if the inventory itself is invalid.
        parser.error(f"invalid inventory: {exc}")
    try:
        base, head = load_json(args.base), load_json(args.head)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"manifest evaluation unavailable: {exc}", file=sys.stderr)
        base, head = None, None
    print(json.dumps(select(jobs, base, head, args.changed_path, args.evaluation_failed)))


if __name__ == "__main__":
    main()
