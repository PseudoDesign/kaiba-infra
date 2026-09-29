import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

spec = importlib.util.spec_from_file_location("kaiba_login", Path(__file__).parents[1] / "client/kaiba.py")
kaiba = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kaiba)


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.config = {
            "caURL": "https://ssh-ca.example.test",
            "rootFingerprint": "a" * 64,
            "sshUserCAFingerprint": "SHA256:" + "A" * 43,
            "issuer": "https://auth.example.test/realms/kaiba",
            "clientID": "kaiba-ssh",
            "principal": "kaiba:person:fixture-subject",
        }
        self.config_path = self.directory / "login.json"
        self.config_path.write_text(json.dumps(self.config))
        self.config_path.chmod(0o600)
        self.agent = {"path": "/run/user/fixture/agent.sock", "device": 1, "inode": 2}
        self.state_path = self.directory / "session.json"
        self.comment = "kaiba-human:" + "a" * 32
        self.cert = "ssh-ed25519-cert-v01@openssh.com Zml4dHVyZQ== " + self.comment
        self.now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
        self.inspection = {
            "Type": "user", "Principals": [self.config["principal"]],
            "SigningKeyFingerprint": self.config["sshUserCAFingerprint"],
            "KeyID": self.config["issuer"] + "#fixture-subject",
            "ValidAfter": (self.now - timedelta(seconds=60)).isoformat(),
            "ValidBefore": (self.now + timedelta(hours=8)).isoformat(),
        }

    def test_public_configuration_is_explicit_and_https_only(self):
        self.assertEqual(kaiba.load_config(self.config_path), self.config)
        for url in ("http://ssh-ca.example.test", "https://user:secret@example.test",
                    "https://example.test/?token=secret", "https://example.test/#fragment"):
            with self.subTest(url=url), self.assertRaises(kaiba.LoginError):
                kaiba.https_url(url)
        self.config["token"] = "must-never-be-used"
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaises(kaiba.LoginError):
            kaiba.load_config(self.config_path)

    def test_writable_or_symlinked_configuration_is_rejected(self):
        self.config_path.chmod(0o666)
        with self.assertRaises(kaiba.LoginError):
            kaiba.load_config(self.config_path)
        self.config_path.chmod(0o600)
        link = self.directory / "config-link"
        link.symlink_to(self.config_path)
        with self.assertRaises(kaiba.LoginError):
            kaiba.load_config(link)

    def test_remote_ssh_session_cannot_obtain_human_identity(self):
        with patch.dict(os.environ, {"SSH_CONNECTION": "192.0.2.1 22 192.0.2.2 1234"}):
            with self.assertRaisesRegex(kaiba.LoginError, "own workstation"):
                kaiba.agent_identity()

    def test_empty_agent_is_valid(self):
        result = kaiba.subprocess.CompletedProcess([], 1, "The agent has no identities.\n", "")
        with patch.object(kaiba.subprocess, "run", return_value=result):
            self.assertEqual(kaiba.agent_keys(), [])

    def test_certificate_binds_identity_and_ca_and_bounded_lifetime(self):
        with patch.object(kaiba, "run", return_value=json.dumps(self.inspection)):
            self.assertTrue(kaiba.inspect_certificate(self.cert, self.config, now=self.now)["active"])
        bad = [
            {"Type": "host"}, {"Principals": ["adam"]},
            {"Principals": [self.config["principal"], "root"]},
            {"SigningKeyFingerprint": "SHA256:wrong"},
            {"KeyID": "email-must-not-be-an-identity@example.test"},
            {"ValidBefore": (self.now + timedelta(hours=9)).isoformat()},
            {"ValidBefore": (self.now - timedelta(seconds=1)).isoformat()},
            {"ValidAfter": (self.now + timedelta(seconds=1)).isoformat()},
        ]
        for changed in bad:
            with self.subTest(changed=changed), patch.object(kaiba, "run", return_value=json.dumps(self.inspection | changed)):
                with self.assertRaises(kaiba.LoginError):
                    kaiba.inspect_certificate(self.cert, self.config, now=self.now)

    def test_status_reports_expired_certificate_without_renewing_it(self):
        expired = self.inspection | {"ValidBefore": (self.now - timedelta(seconds=1)).isoformat()}
        with patch.object(kaiba, "run", return_value=json.dumps(expired)) as run:
            result = kaiba.inspect_certificate(self.cert, self.config, now=self.now, active=False)
        self.assertFalse(result["active"])
        self.assertEqual(run.call_args.args[0], ["step", "ssh", "inspect", "--format", "json"])

    def write_session(self, **extra):
        kaiba.write_state(self.state_path, {"agent": self.agent, "comment": self.comment, "certificate": self.cert} | extra)

    def test_logout_removes_only_the_exact_owned_certificate(self):
        self.write_session()
        unrelated = "ssh-ed25519 b3duZXI= owner@workstation"
        with patch.object(kaiba, "agent_keys", return_value=[unrelated, self.cert]), patch.object(kaiba, "run") as run:
            kaiba.logout(self.state_path, self.agent)
        run.assert_called_once_with(["ssh-add", "-d", "-"], input=self.cert + "\n")
        self.assertFalse(self.state_path.exists())

    def test_logout_refuses_other_agent_or_replaced_certificate(self):
        self.write_session()
        with patch.object(kaiba, "old_socket_stale", return_value=False):
            with self.assertRaises(kaiba.LoginError):
                kaiba.logout(self.state_path, self.agent | {"inode": 3})
        with patch.object(kaiba, "agent_keys", return_value=[self.cert.replace("Zml4dHVyZQ==", "cmVwbGFjZWQ=")]), patch.object(kaiba, "run") as run:
            with self.assertRaises(kaiba.LoginError):
                kaiba.logout(self.state_path, self.agent)
            run.assert_not_called()
        self.assertTrue(self.state_path.exists())

    def test_missing_or_replaced_agent_clears_only_public_state(self):
        for existing in (False, True):
            with self.subTest(replacement=existing):
                old_path = self.directory / "old-agent"
                if existing:
                    old_path.touch()  # A regular file replaced the old socket.
                old_agent = self.agent | {"path": str(old_path)}
                self.write_session(agent=old_agent)
                certificate_path = self.directory / "certificate.pub"
                certificate_path.write_text(self.cert)
                with patch.object(kaiba, "agent_keys") as keys, patch.object(kaiba, "run") as run:
                    self.assertFalse(kaiba.logout(self.state_path, self.agent)["active"])
                    keys.assert_not_called()
                    run.assert_not_called()
                self.assertFalse(self.state_path.exists())
                self.assertFalse(certificate_path.exists())

    def test_live_original_agent_and_uncertain_lookup_cannot_be_forgotten(self):
        live = SimpleNamespace(st_mode=kaiba.stat.S_IFSOCK | 0o600, st_dev=1, st_ino=2)
        with patch.object(Path, "lstat", return_value=live):
            self.assertFalse(kaiba.old_socket_stale(self.agent))
            self.assertTrue(kaiba.old_socket_stale(self.agent | {"inode": 3}))
        with patch.object(Path, "lstat", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                kaiba.old_socket_stale(self.agent)

    def test_interrupted_login_can_be_cleaned_up_without_configuration(self):
        self.write_session(certificate=None)
        with patch.object(kaiba, "agent_keys", return_value=[self.cert]), patch.object(kaiba, "run") as run:
            kaiba.logout(self.state_path, self.agent)
        run.assert_called_once_with(["ssh-add", "-d", "-"], input=self.cert + "\n")

    def test_duplicate_login_never_replaces_existing_key(self):
        self.write_session()
        with patch.object(kaiba, "run") as run:
            with self.assertRaises(kaiba.LoginError):
                kaiba.login(self.config, self.state_path, self.agent)
            run.assert_not_called()

    def test_failed_bootstrap_leaves_unrelated_agent_keys_alone(self):
        with patch.object(kaiba, "run", side_effect=kaiba.LoginError("step failed")), patch.object(kaiba, "agent_keys", return_value=["ssh-ed25519 cHVibGlj owner"]):
            with self.assertRaises(kaiba.LoginError):
                kaiba.login(self.config, self.state_path, self.agent)
        self.assertFalse(self.state_path.exists())

    def test_successful_login_verifies_before_reporting_and_saves_public_material_only(self):
        commands = []
        public_roots = self.directory / "system-roots.pem"
        public_roots.write_text("test-only public roots")
        class Roots:
            cafile = str(public_roots)
        def fake_run(command, **kwargs):
            commands.append(command)
            if command[1:3] == ["ca", "root"]:
                Path(command[3]).write_text("test-only public CA root")
            return ""
        with patch.object(kaiba, "run", side_effect=fake_run), patch.object(kaiba, "owned_keys", return_value=[self.cert]), patch.object(kaiba, "verify_provisioner"), patch.object(kaiba, "inspect_certificate", return_value={"active": True}), patch.object(kaiba, "agent_identity", return_value=self.agent), patch.object(kaiba.ssl, "get_default_verify_paths", return_value=Roots()):
            self.assertTrue(kaiba.login(self.config, self.state_path, self.agent)["active"])
        self.assertEqual(commands[0][-2:], ["--fingerprint", self.config["rootFingerprint"]])
        login = commands[1]
        self.assertIn("--force", login)
        self.assertNotIn("--principal", login)
        self.assertNotIn("--token", login)
        self.assertNotIn("--console", login)
        self.assertEqual(set(json.loads(self.state_path.read_text())), {"agent", "comment", "certificate"})
        self.assertEqual(list(self.directory.glob("login-*")), [])

    def test_provisioner_pin_rejects_changed_issuer_client_or_callback(self):
        provisioner = {
            "name": "kaiba-human", "type": "OIDC", "clientID": "kaiba-ssh",
            "configurationEndpoint": self.config["issuer"] + "/.well-known/openid-configuration",
            "listenAddress": "127.0.0.1:8400",
        }
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return json.dumps({"provisioners": [entry]}).encode()
        for changed in ({}, {"clientID": "another-client"}, {"configurationEndpoint": "https://wrong.example"}, {"listenAddress": "0.0.0.0:8400"}, {"clientSecret": "not-a-public-client"}):
            entry = provisioner | changed
            with self.subTest(changed=changed), patch.object(kaiba.ssl, "create_default_context"), patch.object(kaiba, "build_opener") as opener:
                opener.return_value.open.return_value = Response()
                if changed:
                    with self.assertRaises(kaiba.LoginError):
                        kaiba.verify_provisioner(self.config, self.directory / "trust.pem")
                else:
                    kaiba.verify_provisioner(self.config, self.directory / "trust.pem")


if __name__ == "__main__":
    unittest.main()
