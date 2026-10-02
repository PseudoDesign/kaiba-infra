import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("forgejo_migrate", Path(__file__).parents[1] / "ci/forgejo_migrate.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MigrationTests(unittest.TestCase):
    def test_existing_destination_is_never_overwritten(self):
        class Forge:
            def request(self, method, path, value=None):
                self_test.assertEqual(method, "GET")
                return {"id": 1}
        self_test = self
        with patch.object(m, "github") as source:
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                m.import_repo(Forge(), {"destination": "owner/repo"}, "secret")
            source.assert_not_called()

    def test_visibility_drift_prevents_import(self):
        class Forge:
            def request(self, method, path, value=None):
                self_test.assertEqual(method, "GET")
                return None
        self_test = self
        with patch.object(m, "github", return_value={"full_name": "owner/repo", "private": False}):
            with self.assertRaisesRegex(ValueError, "visibility"):
                m.import_repo(Forge(), {"source": "owner/repo", "destination": "owner/repo", "private": True}, "secret")

    def test_import_preserves_privacy_and_disables_execution(self):
        calls = []
        class Forge:
            def request(self, method, path, value=None):
                calls.append((method, path, value))
                if method == "POST":
                    return {"full_name": "owner/repo", "private": True}
                return None
        with patch.object(m, "github", return_value={"full_name": "owner/repo", "private": True}):
            result = m.import_repo(Forge(), {"source": "owner/repo", "destination": "owner/repo", "private": True}, "secret")
        self.assertFalse(result["authoritative"])
        self.assertTrue(calls[1][2]["private"])
        self.assertFalse(calls[1][2]["mirror"])
        self.assertEqual(calls[-1], ("PATCH", "/repos/owner/repo", {"has_actions": False}))

    def test_refs_detect_missing_extra_and_changed_tags(self):
        result = m.compare_refs({"refs/heads/main": "a", "refs/tags/v1": "b"},
            {"refs/heads/main": "c", "refs/heads/extra": "d"})
        self.assertEqual(result, {"missing": ["refs/tags/v1"], "unexpected": ["refs/heads/extra"], "changed": ["refs/heads/main"]})

    def test_metadata_reports_lost_body_and_missing_issue(self):
        source = [{"number": 1, "title": "one", "body": "evidence", "state": "closed"},
            {"number": 2, "title": "two", "body": "pending", "state": "open"}]
        destination = [{"number": 1, "title": "one", "body": "", "state": "closed"}]
        result = m.compare_records(source, destination, "number", ("title", "body", "state"))
        self.assertEqual(result["missing"], ["2"])
        self.assertEqual(result["changed"], {"1": ["body"]})

    def test_duplicate_metadata_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            m.compare_records([{"number": 1}, {"number": 1}], [], "number", ("title",))

    def test_manifest_rejects_other_origin_and_duplicate_destination(self):
        config = json.loads((Path(__file__).parents[1] / "ci/forgejo-projects.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            config["forge_url"] = "https://git.pseudo.design.attacker.example"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                m.manifest(path)
            config["forge_url"] = "https://git.pseudo.design"
            config["repositories"].append(config["repositories"][0])
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                m.manifest(path)

    def test_credentials_and_receipts_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            m.private_json(path, {"token": "secret"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                m.private_json(path, {})
            path.write_text("secret\n")
            self.assertEqual(m.private_read(path), "secret")
            os.chmod(path, 0o644)
            with self.assertRaises(ValueError):
                m.private_read(path)


if __name__ == "__main__":
    unittest.main()
