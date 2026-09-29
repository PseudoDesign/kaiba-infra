import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "keycloak_admin", Path(__file__).parents[1] / "identity/keycloak_admin.py")
admin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admin)


class CredentialBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.credentials = self.root / "credentials"
        self.credentials.mkdir(mode=0o700)
        self.environment = patch.dict(os.environ, {
            "CREDENTIALS_DIRECTORY": str(self.credentials),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write(self, path, mode):
        path.write_text("synthetic-test-password\n")
        path.chmod(mode)
        return path

    def test_runtime_password_remains_owner_only(self):
        path = self.write(self.root / "runtime-password", 0o600)
        self.assertEqual(admin.private_read(path), "synthetic-test-password\n")
        path.chmod(0o440)
        with self.assertRaises(admin.Refuse):
            admin.private_read(path)

    def test_systemd_read_only_group_delivery_is_supported(self):
        path = self.write(self.credentials / "admin-password", 0o440)
        self.assertEqual(admin.private_read(path), "synthetic-test-password\n")

    def test_systemd_exception_does_not_cover_other_directories(self):
        sibling = self.root / "credentials-other"
        sibling.mkdir()
        path = self.write(sibling / "admin-password", 0o440)
        with self.assertRaises(admin.Refuse):
            admin.private_read(path)

    def test_credentials_reject_world_access_and_group_writes(self):
        for mode in [0o444, 0o660, 0o450, 0o604]:
            with self.subTest(mode=oct(mode)):
                path = self.credentials / f"admin-{mode:o}"
                self.write(path, mode)
                with self.assertRaises(admin.Refuse):
                    admin.private_read(path)

    def test_symlink_and_multiple_links_are_refused(self):
        original = self.write(self.root / "runtime-password", 0o600)
        link = self.credentials / "admin-password"
        link.symlink_to(original)
        with self.assertRaises(OSError):
            admin.private_read(link)
        link.unlink()
        os.link(original, link)
        with self.assertRaises(admin.Refuse):
            admin.private_read(link)

    def test_oversized_state_is_refused_without_echoing_it(self):
        path = self.write(self.root / "runtime-password", 0o600)
        path.write_text("private-fixture-" * 5000)
        with self.assertRaises(admin.Refuse) as result:
            admin.private_read(path)
        self.assertNotIn("private-fixture", str(result.exception))


if __name__ == "__main__":
    unittest.main()
