import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "ci" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


notify = load("hydra_notify_config")
publish = load("hydra_publish")
INVENTORY = json.loads((ROOT / "ci/provisioning-arm64.json").read_text())
DRV = "/nix/store/" + "a" * 32 + "-test.drv"
OUT = "/nix/store/" + "b" * 32 + "-test"
DEPENDENCY = "/nix/store/" + "c" * 32 + "-kernel"


def payload():
    return {"build": 12, "project": "kaiba-provisioning", "jobset": "main",
            "job": "aarch64-linux.copied-storage-vm", "system": "aarch64-linux",
            "finished": True, "buildStatus": 0, "drvPath": DRV,
            "outputs": [{"name": "out", "path": OUT}]}


class NotifyConfigurationTests(unittest.TestCase):
    def test_contexts_are_unique_stable_and_cover_inventory(self):
        result = notify.render("test_only_token\n", INVENTORY)
        contexts = [line for line in result.splitlines() if "context =" in line]
        self.assertEqual(len(contexts), 11)
        self.assertEqual(len(contexts), len(set(contexts)))
        for item in INVENTORY["jobs"]:
            self.assertIn("ci/hydra/kaiba-provisioning/" + item.removeprefix("checks."), result)

    def test_rejects_config_injection_without_echoing_credential(self):
        for token in ("", "secret\nInclude /etc/shadow", "Bearer secret", "secret\r\n"):
            with self.subTest(token=token), self.assertRaises(ValueError) as error:
                notify.render(token, INVENTORY)
            self.assertNotIn("secret", str(error.exception))

    def test_runtime_output_is_private_even_if_existing_file_was_public(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "github-token").write_text("test_only_token")
            output = root / "hydra.conf"
            output.touch(mode=0o644)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": directory}), patch(
                "sys.argv", ["config", "--output", str(output)]
            ):
                notify.main()
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertIn("Bearer test_only_token", output.read_text())


class PublisherTests(unittest.TestCase):
    def test_failed_build_is_not_enqueued_and_duplicate_success_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            spool = Path(directory)
            publish.enqueue(payload() | {"buildStatus": 1}, spool)
            self.assertEqual(list(spool.iterdir()), [])
            publish.enqueue(payload(), spool)
            publish.enqueue(payload(), spool)
            self.assertEqual([path.name for path in spool.iterdir()], ["12.json"])

    def test_rejects_wrong_origin_architecture_job_and_arbitrary_paths(self):
        changes = ({"project": "untrusted"}, {"jobset": "pr-1"}, {"system": "x86_64-linux"},
                   {"job": "aarch64-linux.unreviewed"}, {"build": "../../escape"},
                   {"drvPath": "/etc/shadow"}, {"outputs": []},
                   {"outputs": [{"path": OUT + "/../../etc/shadow"}]})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                publish.validate(payload() | change)

    def test_retry_keeps_failed_publication_then_pushes_complete_build_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_file = root / "token"
            token_file.write_text("test-only-secret")
            spool = root / "queue"
            spool.mkdir()
            publish.enqueue(payload(), spool)
            calls = []

            def run(command, **kwargs):
                calls.append((command, kwargs))
                if command[0] == "nix-store":
                    return subprocess.CompletedProcess(command, 0, DRV + "\n" + DEPENDENCY + "\n")
                self.assertEqual(set(kwargs["input"].splitlines()), {DRV, DEPENDENCY, OUT})
                self.assertEqual(kwargs["env"]["CACHIX_AUTH_TOKEN"], "test-only-secret")
                self.assertNotIn("test-only-secret", " ".join(command))
                if len(calls) == 2:
                    raise subprocess.CalledProcessError(1, command, stderr="test-only-secret")
                return subprocess.CompletedProcess(command, 0)

            with contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertEqual(publish.publish(spool, token_file, "test", run), 1)
                self.assertTrue((spool / "12.json").exists())
                self.assertEqual(publish.publish(spool, token_file, "test", run), 0)
            self.assertNotIn("test-only-secret", log.getvalue())
            self.assertEqual(list(spool.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
