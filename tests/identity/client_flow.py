"""Real Kaiba/step browser login using the VM's existing virtual passkey.

All keys and accounts in this module are disposable VM fixtures. The production
client is invoked unchanged, including its public HTTPS and SSH CA trust checks.
The caller must release its own listener on 127.0.0.1:8400 before calling this.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

from selenium.webdriver.common.by import By


def exercise_client(driver, public_config):
    with tempfile.TemporaryDirectory(prefix="kaiba-client-fixture-") as temporary:
        directory = Path(temporary)
        config = directory / "login.json"
        config.write_text(json.dumps(public_config))
        config.chmod(0o600)
        socket = directory / "agent.sock"
        env = dict(os.environ)
        env.pop("SSH_CONNECTION", None)
        env.pop("SSH_CLIENT", None)
        env.update({
            "SSH_AUTH_SOCK": str(socket), "XDG_STATE_HOME": str(directory / "state"),
            "STEP_OPEN_BROWSER": "0",
            # The VM's system trust contains the nginx test TLS issuer, which
            # deliberately differs from the fingerprint-pinned step-ca root.
            "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
        })
        agent = subprocess.Popen(["ssh-agent", "-D", "-a", str(socket)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        login = None
        def run(*args, success=True):
            result = subprocess.run(args, env=env, text=True, capture_output=True, timeout=30)
            if success:
                assert result.returncode == 0, f"fixture command {args[0]} failed"
            else:
                assert result.returncode != 0, "incorrect public trust was accepted"
            return result.stdout
        try:
            deadline = time.monotonic() + 10
            while not socket.exists():
                assert agent.poll() is None and time.monotonic() < deadline, "fixture agent did not start"
                time.sleep(0.05)
            run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(directory / "unrelated"))
            run("ssh-add", str(directory / "unrelated"))
            before = run("ssh-add", "-L")

            # A wrong bootstrap fingerprint must fail before authentication or
            # addition of a certificate. Keep unrelated agent identities intact.
            wrong = directory / "wrong-root.json"
            wrong.write_text(json.dumps(public_config | {"rootFingerprint": "0" * 64}))
            wrong.chmod(0o600)
            run("kaiba", "--config", str(wrong), "login", success=False)
            assert run("ssh-add", "-L") == before

            stdout = directory / "login.stdout"
            stderr = directory / "login.stderr"
            def safe_login_error():
                # Only surface the wrapper's bounded error lines. step's raw
                # output includes browser URLs and may contain provider data.
                errors = []
                for line in stderr.read_text().splitlines():
                    if line.startswith("kaiba: "):
                        line = re.sub(r"https?://\S+", "<URL>", line)
                        line = re.sub(r"[A-Za-z0-9_+/=-]{32,}", "<redacted>", line)
                        errors.append(line[:250])
                return " | ".join(errors[-3:]) or "no wrapper error recorded"
            with stdout.open("w") as out, stderr.open("w") as err:
                login = subprocess.Popen(["kaiba", "--config", str(config), "login"],
                                         env=env, stdout=out, stderr=err, text=True)
                deadline = time.monotonic() + 60
                authorization_url = None
                while authorization_url is None:
                    assert login.poll() is None, "Kaiba login failed before browser authorization: " + safe_login_error()
                    assert time.monotonic() < deadline, "Kaiba did not produce a browser authorization URL"
                    for line in stderr.read_text().splitlines():
                        if line.startswith(public_config["issuer"] + "/protocol/openid-connect/auth?"):
                            authorization_url = line
                            break
                    time.sleep(0.1)
                query = parse_qs(urlsplit(authorization_url).query)
                assert query["client_id"] == ["kaiba-ssh"]
                assert query["redirect_uri"] == ["http://127.0.0.1:8400"]
                assert query["code_challenge_method"] == ["S256"]
                driver.delete_all_cookies()
                driver.get(authorization_url)
                assert not driver.find_elements(By.CSS_SELECTOR, "input[type=password]")
                for button in driver.find_elements(By.ID, "authenticateWebAuthnButton"):
                    button.click()
                login_result = login.wait(timeout=90)
                if login_result:
                    assert run("ssh-add", "-L") == before, "failed issuance changed another agent identity"
                    failed_state = directory / "state/kaiba"
                    assert not (failed_state / "session.json").exists(), "failed issuance retained a session"
                    assert not (failed_state / "certificate.pub").exists(), "failed issuance retained a certificate"
                assert login_result == 0, "Real Kaiba/step passkey login failed: " + safe_login_error()

            result = json.loads(run("kaiba", "--config", str(config), "status"))
            assert result["active"] and result["principal"] == public_config["principal"]
            state = directory / "state/kaiba"
            assert Path(result["certificateFile"]) == state / "certificate.pub"
            # This is public material only; the ephemeral private key was added
            # directly to the agent by the production step ssh login command.
            assert {path.name for path in state.iterdir()} == {"lock", "session.json", "certificate.pub"}
            run("ssh-keygen", "-L", "-f", str(state / "certificate.pub"))
            assert len(run("ssh-add", "-L").splitlines()) == len(before.splitlines()) + 1
            run("kaiba", "--config", str(config), "logout")
            assert run("ssh-add", "-L") == before, "logout altered another agent identity"
            assert not (state / "certificate.pub").exists()
            assert not (state / "session.json").exists()
            assert not json.loads(run("kaiba", "--config", str(config), "status"))["active"]
            print("Real Kaiba/step login verified TLS roots, issuer/client pins, PKCE, SSH CA signature, local agent storage and selective logout.")
        finally:
            if login is not None and login.poll() is None:
                login.terminate()
                login.wait(timeout=10)
            agent.terminate()
            agent.wait(timeout=10)
