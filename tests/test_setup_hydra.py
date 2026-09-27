import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_hydra", ROOT / "ci/setup_hydra.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
DEFINITIONS = json.loads((ROOT / "ci/hydra-jobsets.json").read_text())


class MemoryHydra(setup.Hydra):
    def __init__(self):
        self.state = {}
        self.writes = []

    def request(self, method, path, data=None):
        if method == "GET":
            return self.state.get(path)
        self.writes.append((path, data))
        self.state[path] = {key: value for key, value in data.items() if key != "visible"}
        if path.startswith("/project/"):
            self.state[path]["hidden"] = False
        else:
            self.state[path]["visible"] = True


class SetupTests(unittest.TestCase):
    def test_default_creates_disabled_provisioning_and_repeat_is_noop(self):
        client = MemoryHydra()
        desired = setup.changes(DEFINITIONS, "infrastructure")
        with contextlib.redirect_stdout(io.StringIO()):
            client.reconcile(desired)
            client.reconcile(desired)
        self.assertEqual(len(client.writes), 4)
        self.assertEqual(client.state["/jobset/kaiba-provisioning/main"]["enabled"], 0)
        self.assertEqual(client.state["/jobset/kaiba-infra/main"]["enabled"], 1)

    def test_provisioning_stage_and_return_to_infrastructure(self):
        client = MemoryHydra()
        with contextlib.redirect_stdout(io.StringIO()):
            client.reconcile(setup.changes(DEFINITIONS, "provisioning"))
            self.assertEqual(client.state["/jobset/kaiba-provisioning/main"]["enabled"], 1)
            client.reconcile(setup.changes(DEFINITIONS, "infrastructure"))
        self.assertEqual(client.state["/jobset/kaiba-provisioning/main"]["enabled"], 0)

    def test_preview_does_not_authenticate(self):
        with patch.object(setup.Hydra, "request") as request, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main([]), 0)
        request.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["/jobset/kaiba-provisioning/main"]["enabled"], 0)

    def test_enable_requires_successful_finished_infrastructure_build(self):
        for build in (None, {"finished": 0, "buildstatus": 0}, {"finished": 1, "buildstatus": 1}):
            with self.subTest(build=build), patch.object(setup.Hydra, "request", side_effect=[{}, build]) as request, \
                    patch.object(setup.getpass, "getpass", return_value="test"), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(setup.main(["--apply", "--stage", "provisioning"]), 1)
                self.assertEqual([call.args[0] for call in request.call_args_list], ["POST", "GET"])

    def test_readback_failure_is_not_success(self):
        client = setup.Hydra("http://localhost:3000")
        with patch.object(client, "request", side_effect=[None, {}, {"enabled": 0}]):
            with self.assertRaisesRegex(RuntimeError, "readback"):
                client.reconcile(setup.changes(DEFINITIONS, "infrastructure")[:1])

    def test_remote_http_and_embedded_credentials_are_rejected(self):
        for url in ("http://hydra.pseudo.design", "https://user:secret@hydra.pseudo.design", "https://hydra.pseudo.design/path"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                setup.Hydra(url)

    def test_redirects_only_allow_same_origin_reads(self):
        handler = setup.SafeRedirect()
        get = urllib.request.Request("https://hydra.pseudo.design/latest")
        self.assertIsNotNone(handler.redirect_request(get, None, 302, "", {}, "https://hydra.pseudo.design/build/1"))
        self.assertIsNone(handler.redirect_request(get, None, 302, "", {}, "https://other.example/build/1"))
        post = urllib.request.Request("https://hydra.pseudo.design/login", data=b"secret")
        self.assertIsNone(handler.redirect_request(post, None, 302, "", {}, "https://hydra.pseudo.design/login/"))
        redirected = handler.redirect_request(post, None, 302, "", {}, "https://hydra.pseudo.design/current-user")
        self.assertEqual(redirected.get_method(), "GET")
        self.assertIsNone(redirected.data)

    def test_http_failure_does_not_echo_server_body(self):
        client = setup.Hydra("http://localhost:3000")
        error = urllib.error.HTTPError(client.url, 403, "Forbidden", {}, io.BytesIO(b"secret"))
        with patch.object(client.opener, "open", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403") as failure:
                client.request("POST", "/login", {"password": "secret"})
        self.assertNotIn("secret", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
