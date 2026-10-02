import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "ci"))
import hydra_forgejo_runs as c
import forgejo_git_credential as git_credential


class ForgejoAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.run = {"id": 42, "index_in_repo": 7, "workflow_id": "ci.yml", "commit_sha": self.sha,
            "repository": {"full_name": c.REPOSITORY}, "status": "running", "event": "pull_request",
            "need_approval": False, "is_fork_pull_request": False, "is_ref_deleted": False}
        self.task = {"id": 99, "run_number": 7, "workflow_id": "ci.yml", "head_sha": self.sha,
            "name": f"ARM64 checks on Hydra ({self.sha})", "status": "running", "event": "pull_request"}

    def test_immutable_jobset_uses_task_attempt_and_exact_sha(self):
        value = c.request_for_task(self.task, self.run)
        self.assertEqual(value["name"], "ci-7-99")
        self.assertEqual(value["flake"], f"git+https://git.pseudo.design/{c.REPOSITORY}.git?rev={self.sha}")
        self.task["id"] = 100
        self.assertEqual(c.request_for_task(self.task, self.run)["name"], "ci-7-100")

    def test_blocked_cancelled_unapproved_runs_are_not_admitted(self):
        for field, value in [("status", "cancelled"), ("status", "blocked"), ("need_approval", True), ("is_ref_deleted", True)]:
            run = {**self.run, field: value}
            self.assertIsNone(c.request_for_task(self.task, run))
        self.run["is_fork_pull_request"] = True
        self.assertIsNone(c.request_for_task(self.task, self.run))
        self.run["approved_by"] = 123
        self.assertIsNotNone(c.request_for_task(self.task, self.run))

    def test_workflow_repository_run_and_sha_must_match(self):
        for field, value in [("workflow_id", "unreviewed.yml"), ("head_sha", "b" * 40), ("run_number", 8), ("event", "push")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.request_for_task({**self.task, field: value}, self.run)
        with self.assertRaises(ValueError):
            c.request_for_task(self.task, {**self.run, "repository": {"full_name": "attacker/repo"}})

    def test_only_main_pushes_are_admitted(self):
        self.run.update(event="push", prettyref="topic")
        self.task["event"] = "push"
        self.assertIsNone(c.request_for_task(self.task, self.run))
        self.run["prettyref"] = "main"
        self.assertIsNotNone(c.request_for_task(self.task, self.run))

    def test_token_is_not_given_to_another_host_or_protocol(self):
        self.assertEqual(git_credential.credential({"protocol": "http", "host": "git.pseudo.design"}, "secret"), "")
        self.assertEqual(git_credential.credential({"protocol": "https", "host": "github.com"}, "secret"), "")
        self.assertIn("password=secret", git_credential.credential({"protocol": "https", "host": "git.pseudo.design"}, "secret"))

    def test_hydra_evaluation_cannot_substitute_revision_or_duplicate_build(self):
        valid = {"flake": c.flake(self.sha) + "&narHash=sha256-example", "builds": list(range(1, 11))}
        self.assertEqual(c.validate_evaluation(valid, self.sha), list(range(1, 11)))
        for value in [
            {**valid, "flake": c.flake("b" * 40)},
            {**valid, "flake": c.flake(self.sha) + "&rev=" + self.sha},
            {**valid, "builds": [1] * 10},
            {**valid, "builds": [1]},
            {**valid, "flake": c.flake(self.sha).replace("git.pseudo.design", "attacker.example")},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.validate_evaluation(value, self.sha)


if __name__ == "__main__":
    unittest.main()
