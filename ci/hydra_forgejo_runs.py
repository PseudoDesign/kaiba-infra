#!/usr/bin/env python3
"""Admit running Forgejo waiters to immutable Hydra jobsets and report results.

Uses Forgejo 15's task IDs to distinguish attempts; GitHub run-attempt fields
do not exist in this API. Approval, repository, workflow and commit are checked
again before reporting. Failed API deliveries retry on the next timer tick.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

from forgejo_migrate import Forge
from hydra_ci_runs import reconcile, positive
from setup_hydra import Hydra

REPOSITORY = "PseudoDesign/kaiba-provisioning"
ORIGIN = "https://git.pseudo.design"
PROJECT = "kaiba-provisioning"
WAITER = re.compile(r"ARM64 checks on Hydra \(([0-9a-f]{40})\)")
SHA = re.compile(r"[0-9a-f]{40}")
JOBS = {
    "stable-verifier-aarch64-kexec-vm", "stable-handoff-aarch64-kexec-file-vm",
    "device-secret-target-luks-vm", "device-secret-storage-development-vm",
    "enrollment-storage-vm", "copied-storage-vm", "device-secret-offline-storage-vm",
    "device-secret-execution-vm", "stable-campaign-provisioner-unsigned-artifacts",
    "device-secret-target-artifacts",
}


def validate_evaluation(evaluation, sha):
    reference = urllib.parse.urlsplit(evaluation.get("flake", ""))
    expected = urllib.parse.urlsplit(flake(sha))
    parameters = urllib.parse.parse_qs(reference.query, strict_parsing=True)
    if (reference.scheme != expected.scheme or reference.netloc != expected.netloc
            or reference.path != expected.path or reference.fragment
            or parameters.get("rev") != [sha]
            or set(parameters) - {"rev", "narHash", "lastModified", "revCount"}
            or any(len(values) != 1 for values in parameters.values())):
        raise ValueError("Hydra evaluation source differs from admitted commit")
    ids = evaluation.get("builds")
    if (not isinstance(ids, list) or len(ids) != len(JOBS)
            or any(not positive(value) for value in ids) or len(set(ids)) != len(ids)):
        raise ValueError("Hydra evaluation must contain the ten distinct planned builds")
    return ids


def flake(sha):
    if not SHA.fullmatch(sha):
        raise ValueError("full commit SHA required")
    return f"git+{ORIGIN}/{REPOSITORY}.git?rev={sha}"


def pages(forge, path):
    for page in range(1, 101):
        response = forge.request("GET", f"/repos/{REPOSITORY}{path}?limit=50&page={page}")
        rows = response.get("workflow_runs") if isinstance(response, dict) else None
        if not isinstance(rows, list):
            raise ValueError("unexpected Forgejo run/task list")
        yield from rows
        if len(rows) < 50:
            return
    raise RuntimeError("Forgejo pagination incomplete")


def request_for_task(task, run):
    match = WAITER.fullmatch(task.get("name", ""))
    if not match or task.get("status") != "running":
        return None
    if (run.get("status") != "running" or run.get("is_ref_deleted") is not False
            or run.get("need_approval") is not False
            or run.get("is_fork_pull_request") and not positive(run.get("approved_by"))):
        return None
    sha = match[1]
    if (run.get("repository", {}).get("full_name") != REPOSITORY
            or run.get("workflow_id") != "ci.yml" or task.get("workflow_id") != "ci.yml"
            or run.get("event") not in {"push", "pull_request", "workflow_dispatch"}
            or task.get("event") != run["event"]
            or task.get("run_number") != run.get("index_in_repo")
            or run.get("commit_sha") != sha or task.get("head_sha") != sha
            or not positive(run.get("id")) or not positive(task.get("id"))
            or not positive(run.get("index_in_repo"))):
        raise ValueError("Forgejo waiter identity differs from its admitted run")
    if run["event"] == "push" and run.get("prettyref") != "main":
        return None
    return {
        "name": f'ci-{run["index_in_repo"]}-{task["id"]}',
        "description": f'Forgejo run {run["id"]}, task {task["id"]}, commit {sha}',
        "type": 1, "flake": flake(sha), "visible": 1, "enabled": 1,
        "checkinterval": 0, "schedulingshares": 1, "keepnr": 0,
    }


def report(forge, hydra, desired, sha):
    jobset = hydra.request("GET", f'/jobset/{PROJECT}/{desired["name"]}')
    if (jobset is None or jobset.get("flake") != flake(sha)
            or jobset.get("project") != PROJECT or jobset.get("name") != desired["name"]):
        raise ValueError("Hydra jobset source changed")
    error = jobset.get("errormsg") or jobset.get("fetcherrormsg")
    evaluations = hydra.request("GET", f'/jobset/{PROJECT}/{desired["name"]}/evals')
    rows = evaluations.get("evals", []) if isinstance(evaluations, dict) else []
    if not isinstance(rows, list) or len(rows) > 1:
        raise ValueError("immutable jobset has multiple evaluations")
    if error:
        forge.request("POST", f"/repos/{REPOSITORY}/statuses/{sha}", {
            "context": "ci/hydra/evaluation", "state": "error", "description": "Hydra evaluation failed",
            "target_url": f"https://hydra.pseudo.design/jobset/{PROJECT}/{desired['name']}"})
        return True
    if not rows:
        return False
    builds = []
    seen = set()
    for build_id in validate_evaluation(rows[0], sha):
        build = hydra.request("GET", f"/build/{build_id}")
        job = build.get("job", "").removeprefix("aarch64-linux.")
        if (build.get("id") != build_id or build.get("project") != PROJECT
                or build.get("system") != "aarch64-linux" or job not in JOBS
                or build.get("job") != "aarch64-linux." + job or job in seen):
            raise ValueError("unexpected Hydra build identity")
        seen.add(job)
        builds.append((build_id, build))
    # Validate the whole evaluation before publishing any successful status.
    for build_id, build in builds:
        state = "pending" if build.get("finished") != 1 else "success" if build.get("buildstatus") == 0 else "failure"
        forge.request("POST", f"/repos/{REPOSITORY}/statuses/{sha}", {
            "context": f"ci/hydra/{PROJECT}/" + build["job"], "state": state,
            "description": "Hydra " + state, "target_url": f"https://hydra.pseudo.design/build/{build_id}"})
    return all(build.get("finished") == 1 for _, build in builds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hydra-url", default="http://127.0.0.1:3000")
    parser.add_argument("--username", default="adam")
    args = parser.parse_args()
    credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
    forge = Forge(ORIGIN, (credentials / "forge-token").read_text().strip())
    hydra = Hydra(args.hydra_url)
    hydra.request("POST", "/login", {"username": args.username,
        "password": (credentials / "hydra-password").read_text().rstrip("\n")})
    runs = {run["index_in_repo"]: run for run in pages(forge, "/actions/runs")}
    tasks = list(pages(forge, "/actions/tasks"))
    state = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/kaiba-hydra-forgejo"))
    failures = 0
    for task in tasks:
        if task.get("status") != "running" or not WAITER.fullmatch(task.get("name", "")):
            continue
        try:
            listed = runs.get(task.get("run_number"))
            if listed is None:
                raise ValueError("waiter run not found")
            run = forge.request("GET", f'/repos/{REPOSITORY}/actions/runs/{listed["id"]}')
            desired = request_for_task(task, run)
            if desired is None:
                continue
            reconcile(hydra, desired)
            record = state / (desired["name"] + ".json")
            value = {"desired": desired, "run_id": run["id"], "task_id": task["id"], "sha": task["head_sha"]}
            if record.exists():
                if json.loads(record.read_text()) != value:
                    raise ValueError("previous admission changed")
            else:
                with record.open("x") as handle:
                    json.dump(value, handle)
            # Recheck server admission after reconciliation; a cancelled task
            # never publishes success merely because its builds completed.
            fresh = forge.request("GET", f'/repos/{REPOSITORY}/actions/runs/{run["id"]}')
            if request_for_task(task, fresh) != desired:
                continue
            report(forge, hydra, desired, task["head_sha"])
        except (ValueError, RuntimeError, OSError, KeyError):
            print("Cannot reconcile Forgejo waiter; no success assumed", file=sys.stderr)
            failures += 1
    # A waiter can finish between timer ticks. Keep its admission until final
    # statuses are delivered; cancelled/replaced tasks cannot finish an attempt.
    by_id = {task["id"]: task for task in tasks}
    for record in state.glob("ci-*.json"):
        try:
            value = json.loads(record.read_text())
            task = by_id.get(value["task_id"])
            if task is None or task.get("status") != "success" or task.get("head_sha") != value["sha"]:
                continue
            run = forge.request("GET", f'/repos/{REPOSITORY}/actions/runs/{value["run_id"]}')
            if (run.get("commit_sha") != value["sha"] or run.get("repository", {}).get("full_name") != REPOSITORY
                    or run.get("status") == "cancelled" or run.get("need_approval") is not False):
                continue
            if report(forge, hydra, value["desired"], value["sha"]):
                record.unlink()
        except (ValueError, RuntimeError, OSError, KeyError):
            print("Final Forgejo status delivery failed; admission retained for retry", file=sys.stderr)
            failures += 1
    return int(failures > 0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, KeyError):
        print("Forgejo/Hydra discovery failed; retry next tick", file=sys.stderr)
        raise SystemExit(1)
