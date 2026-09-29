import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ssh_ca_log", Path(__file__).parents[1] / "identity/ssh-ca-log.py")
log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log)


class LogRedactionTests(unittest.TestCase):
    def test_bearer_fields_never_reach_audit_output(self):
        value = {"ott": "sensitive", "nested": [{"Authorization": "Bearer sensitive"}],
                 "serial": 42, "principals": ["kaiba:person:subject"]}
        self.assertEqual(log.redact(value), {"nested": [{}], "serial": 42,
                                             "principals": ["kaiba:person:subject"]})

    def test_tokens_in_diagnostics_are_redacted(self):
        token = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZGFtIn0.c2lnbmF0dXJl"
        self.assertEqual(log.redact("bad token: " + token), "bad token: [redacted bearer token]")
        self.assertEqual(log.redact({"message": token}), {"message": "[redacted bearer token]"})


if __name__ == "__main__":
    unittest.main()
