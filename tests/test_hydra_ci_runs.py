import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

SCRIPTS = Path(__file__).resolve().parents[1] / "ci"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("hydra_ci_runs", SCRIPTS / "hydra_ci_runs.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
WORKFLOW_ID = 123
HEAD = "a" * 40
MERGE = "b" * 40


def run(event="pull_request"):
    return {"id": 42, "run_attempt": 2, "workflow_id": WORKFLOW_ID, "path": ci.WORKFLOW,
            "repository": {"full_name": ci.REPOSITORY}, "head_sha": HEAD,
            "event": event, "status": "in_progress", "conclusion": None, "pull_requests": []}


def job(sha=MERGE):
    return {"id": 99, "run_id": 42, "run_attempt": 2,
            "name": f"ARM64 checks on Hydra ({sha})", "status": "in_progress", "conclusion": None}


class GitHubFixture:
    def __init__(self, jobs=None, commit=None):
        self.jobs = [job()] if jobs is None else jobs
        self.commit = {"sha": MERGE, "parents": [{"sha": "c" * 40}, {"sha": HEAD}]} if commit is None else commit
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        if path.startswith("/actions/runs/"):
            return {"jobs": self.jobs}
        if path.startswith("/commits/"):
            return self.commit
        raise AssertionError(path)


class DiscoveryTests(unittest.TestCase):
    def test_fork_pr_uses_exact_merge_with_run_head_without_pull_requests_array(self):
        github = GitHubFixture()
        desired = ci.request_for_run(github, run(), WORKFLOW_ID)
        self.assertEqual(desired["name"], "ci-42-2")
        self.assertEqual(desired["flake"], f"github:{ci.REPOSITORY}/{MERGE}")
        self.assertEqual(desired["enabled"], 2)
        self.assertEqual(desired["keepnr"], 0)
        self.assertIn("/attempts/2/jobs?", github.paths[0])

    def test_manual_run_must_use_dispatched_sha(self):
        desired = ci.request_for_run(GitHubFixture([job(HEAD)]), run("workflow_dispatch"), WORKFLOW_ID)
        self.assertTrue(desired["flake"].endswith(HEAD))
        with self.assertRaises(ValueError):
            ci.request_for_run(GitHubFixture(), run("workflow_dispatch"), WORKFLOW_ID)

    def test_unadmitted_cancelled_and_other_workflows_do_not_schedule(self):
        for change in ({"status": "queued"}, {"status": "waiting"}, {"status": "action_required"},
                       {"status": "completed"}, {"conclusion": "cancelled"}, {"event": "push"},
                       {"event": "pull_request_target"}):
            github = GitHubFixture()
            self.assertIsNone(ci.request_for_run(github, run() | change, WORKFLOW_ID))
            self.assertEqual(github.paths, [])
        for change in ({"workflow_id": 999}, {"repository": {"full_name": "attacker/repo"}},
                       {"path": ".github/workflows/other.yml"}, {"run_attempt": True},
                       {"id": "../escape"}, {"head_sha": "main"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                ci.request_for_run(GitHubFixture(), run() | change, WORKFLOW_ID)

    def test_only_one_running_waiter_in_exact_attempt_can_request_work(self):
        for change in ({"status": "queued"}, {"status": "completed"}, {"conclusion": "cancelled"},
                       {"name": "ARM64 checks on Hydra (main)"}, {"name": "ARM64 checks on Hydra"}):
            self.assertIsNone(ci.request_for_run(GitHubFixture([job() | change]), run(), WORKFLOW_ID))
        for jobs in ([job(), job()], [job() | {"run_attempt": 1}], [job() | {"run_id": 41}]):
            with self.assertRaises(ValueError):
                ci.request_for_run(GitHubFixture(jobs), run(), WORKFLOW_ID)

    def test_wrong_merge_head_or_non_merge_cannot_schedule(self):
        for commit in ({"sha": MERGE, "parents": [{"sha": HEAD}]},
                       {"sha": MERGE, "parents": [{"sha": HEAD}, {"sha": "d" * 40}]},
                       {"sha": HEAD, "parents": [{"sha": "c" * 40}, {"sha": HEAD}]}):
            with self.assertRaises(ValueError):
                ci.request_for_run(GitHubFixture(commit=commit), run(), WORKFLOW_ID)

    def test_pagination_preserves_all_results_and_fails_when_truncated(self):
        class Pages:
            def get(self, path):
                return {"jobs": list(range(100)) if path.endswith("page=1") else [100]}
        self.assertEqual(list(ci.pages(Pages(), "/jobs", "jobs")), list(range(101)))
        with patch.object(Pages, "get", return_value={"jobs": list(range(100))}), self.assertRaises(RuntimeError):
            list(ci.pages(Pages(), "/jobs", "jobs"))

    def test_bad_request_does_not_block_independent_runs(self):
        github = GitHubFixture()
        good = ci.request_for_run(github, run(), WORKFLOW_ID)
        with patch.object(ci, "pages", return_value=[run(), run()]), patch.object(
            ci, "request_for_run", side_effect=[ValueError("bad merge"), good]
        ):
            requests, failures = ci.discover(github, WORKFLOW_ID)
        self.assertEqual(requests, [good])
        self.assertEqual(failures, 1)


class ReconcileTests(unittest.TestCase):
    def test_one_shot_is_created_once_and_never_reenabled_or_repointed(self):
        desired = ci.request_for_run(GitHubFixture(), run(), WORKFLOW_ID)

        class Hydra:
            current = None
            writes = 0

            def request(self, method, path, data=None):
                if method == "PUT":
                    self.current = data.copy()
                    self.writes += 1
                return self.current

        hydra = Hydra()
        ci.reconcile(hydra, desired)
        hydra.current["enabled"] = 0
        ci.reconcile(hydra, desired)
        self.assertEqual(hydra.writes, 1)
        hydra.current["flake"] = "github:attacker/repo/main"
        with self.assertRaises(RuntimeError):
            ci.reconcile(hydra, desired)
        self.assertEqual(hydra.writes, 1)


class CredentialTests(unittest.TestCase):
    def test_http_errors_and_redirects_do_not_leak_credentials(self):
        failure = urllib.error.HTTPError(ci.API, 403, "private error", {}, io.BytesIO(b"secret response"))
        client = ci.GitHub("test_only_token")
        with patch.object(client.opener, "open", side_effect=failure), self.assertRaisesRegex(RuntimeError, "HTTP 403") as error:
            client.get("/actions/runs")
        self.assertNotIn("secret", str(error.exception))
        for path in ("https://evil.test", "//evil.test", "/../other"):
            with self.assertRaises(ValueError):
                client.get(path)
        request = urllib.request.Request(ci.API)
        self.assertIsNone(ci.NoRedirect().redirect_request(request, None, 302, "", {}, "https://evil.test"))


if __name__ == "__main__":
    unittest.main()
