#!/usr/bin/env python3
"""Create immutable Hydra jobsets for running GitHub PR/manual CI waiters."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

from setup_hydra import Hydra


REPOSITORY = "PseudoDesign/kaiba-provisioning"
PROJECT = "kaiba-provisioning"
API = f"https://api.github.com/repos/{REPOSITORY}"
WORKFLOW = ".github/workflows/ci.yml"
WAITER = re.compile(r"ARM64 checks on Hydra \(([0-9a-f]{40})\)")
SHA = re.compile(r"[0-9a-f]{40}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self, token):
        if not re.fullmatch(r"[A-Za-z0-9_]+", token):
            raise ValueError("GitHub credential must be a single token")
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def get(self, path):
        if not path.startswith("/") or path.startswith("//") or ".." in path:
            raise ValueError("invalid GitHub API path")
        request = urllib.request.Request(API + path, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "kaiba-hydra-ci-runs",
            "X-GitHub-Api-Version": "2022-11-28", "Authorization": "Bearer " + self.token,
        })
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"GitHub API returned HTTP {error.code}") from None


def positive(value):
    return type(value) is int and value > 0


def pages(github, path, field):
    separator = "&" if "?" in path else "?"
    for page in range(1, 11):
        response = github.get(f"{path}{separator}per_page=100&page={page}")
        rows = response.get(field)
        if not isinstance(rows, list):
            raise ValueError("invalid GitHub list response")
        yield from rows
        if len(rows) < 100:
            return
    raise RuntimeError("GitHub pagination limit reached; discovery is incomplete")


def validate_run(run, workflow_id):
    if (run.get("workflow_id") != workflow_id or run.get("path") != WORKFLOW
            or run.get("repository", {}).get("full_name") != REPOSITORY
            or not positive(run.get("id")) or not positive(run.get("run_attempt"))
            or not isinstance(run.get("head_sha"), str) or not SHA.fullmatch(run["head_sha"])):
        raise ValueError("unexpected workflow run identity")


def request_for_run(github, run, workflow_id):
    # A running waiter proves GitHub has admitted this particular run/attempt.
    # Pending approval, queued, cancelled and completed runs cannot request work.
    if (run.get("event") not in {"pull_request", "workflow_dispatch"}
            or run.get("status") != "in_progress" or run.get("conclusion") is not None):
        return None
    validate_run(run, workflow_id)
    path = f'/actions/runs/{run["id"]}/attempts/{run["run_attempt"]}/jobs'
    waiters = []
    for job in pages(github, path, "jobs"):
        match = WAITER.fullmatch(job.get("name", ""))
        if not match or job.get("status") != "in_progress" or job.get("conclusion") is not None:
            continue
        if (job.get("run_id") != run["id"] or job.get("run_attempt") != run["run_attempt"]
                or not positive(job.get("id"))):
            raise ValueError("waiter belongs to a different run or attempt")
        waiters.append(match[1])
    if not waiters:
        return None
    if len(waiters) != 1:
        raise ValueError("multiple Hydra waiters for one run attempt")
    sha = waiters[0]
    if run["event"] == "workflow_dispatch":
        if sha != run["head_sha"]:
            raise ValueError("manual waiter revision differs from the dispatched commit")
    else:
        # PR workflows check out a synthetic merge commit, while the run API's
        # head_sha names the PR head. Bind both, including for forks (whose
        # pull_requests array can be empty). Never use a moving pull/N/merge ref.
        commit = github.get(f"/commits/{sha}")
        parents = commit.get("parents")
        if (commit.get("sha") != sha or not isinstance(parents, list) or len(parents) != 2
                or parents[1].get("sha") != run["head_sha"]):
            raise ValueError("PR waiter is not a merge of this run's head commit")
    return {
        "name": f'ci-{run["id"]}-{run["run_attempt"]}',
        "description": f'GitHub {run["event"]} run {run["id"]}, attempt {run["run_attempt"]}',
        "type": 1, "flake": f"github:{REPOSITORY}/{sha}", "visible": 1,
        # Trigger once through the API; zero interval disables automatic polls.
        # Native enabled=2 removes a live Pid from this Hydra version's evaluator
        # map before its reaper finishes, causing ECHILD and an abort on Ace.
        "enabled": 1, "checkinterval": 0, "schedulingshares": 1, "keepnr": 0,
    }


def reconcile(hydra, desired):
    path = f'/jobset/{PROJECT}/{desired["name"]}'
    current = hydra.request("GET", path)
    if current is None:
        hydra.request("PUT", path, desired)
        current = hydra.request("GET", path)
    # Never silently repoint or re-enable an existing run attempt. Triggering
    # is recoverable if the service stopped after creation, and idempotent if
    # the prior trigger succeeded but its HTTP response was lost.
    for key in ("name", "type", "flake", "visible", "enabled", "checkinterval", "schedulingshares", "keepnr"):
        if current is None or current.get(key) != desired[key]:
            raise RuntimeError(f"Hydra run jobset readback differs: {key}")
    for key in ("lastcheckedtime", "triggertime", "starttime"):
        if key not in current or current[key] is not None and (type(current[key]) is not int or current[key] < 0):
            raise RuntimeError("Hydra jobset lacks valid evaluation scheduling state")
    if not any(current[key] for key in ("lastcheckedtime", "triggertime", "starttime")):
        response = hydra.request("POST", f'/api/push?jobsets={PROJECT}:{desired["name"]}')
        if response.get("jobsetsTriggered") != [f'{PROJECT}:{desired["name"]}']:
            raise RuntimeError("Hydra did not acknowledge the run evaluation trigger")
    print(f'Configured {PROJECT}/{desired["name"]}', flush=True)


def discover(github, workflow_id):
    requests = []
    failures = 0
    for run in pages(github, f"/actions/workflows/{workflow_id}/runs?status=in_progress", "workflow_runs"):
        try:
            desired = request_for_run(github, run, workflow_id)
            if desired is not None:
                requests.append(desired)
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            # One malformed/stale PR must not prevent independent runs from
            # scheduling. Retry transient API failures on the next timer tick.
            run_id = run.get("id") if positive(run.get("id")) else "unknown"
            print(f"Cannot admit GitHub run {run_id}: {error}", file=sys.stderr)
            failures += 1
    return requests, failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-id", type=int, required=True)
    parser.add_argument("--hydra-url", default="http://localhost:3000")
    parser.add_argument("--username", required=True)
    args = parser.parse_args(argv)
    try:
        if not positive(args.workflow_id):
            raise ValueError("a positive workflow ID is required")
        credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
        github = GitHub((credentials / "github-token").read_text().strip())
        requests, failures = discover(github, args.workflow_id)
        if requests:
            hydra = Hydra(args.hydra_url)
            hydra.request("POST", "/login", {
                "username": args.username,
                "password": (credentials / "hydra-password").read_text().rstrip("\n"),
            })
            for desired in requests:
                try:
                    reconcile(hydra, desired)
                except (OSError, ValueError, RuntimeError) as error:
                    print(f'Cannot configure {desired["name"]}: {error}', file=sys.stderr)
                    failures += 1
        return int(failures > 0)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"Hydra CI discovery failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
