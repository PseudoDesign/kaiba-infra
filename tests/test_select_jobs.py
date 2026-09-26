import importlib.util
from pathlib import Path
import unittest

module_path = Path(__file__).resolve().parents[1] / "ci" / "select_jobs.py"
spec = importlib.util.spec_from_file_location("select_jobs", module_path)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

JOBS = ["checks.aarch64-linux.a", "checks.aarch64-linux.b"]
BASE = {job: "/nix/store/" + chr(97 + i) * 32 + "-test.drv" for i, job in enumerate(JOBS)}


class SelectionTests(unittest.TestCase):
    def test_changed_derivation_selects_one(self):
        head = {**BASE, JOBS[1]: "/nix/store/" + "c" * 32 + "-test.drv"}
        self.assertEqual(selector.select(JOBS, BASE, head)["jobs"], [JOBS[1]])

    def test_identical_derivations_select_none(self):
        self.assertEqual(selector.select(JOBS, BASE, BASE)["jobs"], [])

    def test_missing_manifest_job_selects_all(self):
        self.assertEqual(selector.select(JOBS, BASE, {JOBS[0]: BASE[JOBS[0]]})["mode"], "all")

    def test_invalid_derivation_selects_all(self):
        self.assertEqual(selector.select(JOBS, BASE, {**BASE, JOBS[0]: "unknown"})["jobs"], JOBS)

    def test_shared_change_selects_all(self):
        self.assertEqual(selector.select(JOBS, BASE, BASE, ["modules/base.nix"])["jobs"], JOBS)

    def test_evaluation_failure_selects_all(self):
        self.assertEqual(selector.select(JOBS, BASE, BASE, evaluation_failed=True)["mode"], "all")

    def test_invalid_diff_path_selects_all(self):
        self.assertEqual(selector.select(JOBS, BASE, BASE, ["../outside"])["mode"], "all")

    def test_duplicate_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            selector.parse_inventory({"jobs": [JOBS[0], JOBS[0]]})


if __name__ == "__main__":
    unittest.main()
