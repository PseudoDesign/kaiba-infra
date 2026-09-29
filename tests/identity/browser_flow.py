"""Exercise native Keycloak enrollment and OAuth with virtual WebAuthn keys."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

fixture = json.loads(Path("/tmp/enrollment.json").read_text())
origin = "https://acme.test"
callback = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        callback.clear()
        callback.update(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Kaiba test callback")
    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 8400), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
options = webdriver.ChromeOptions()
for flag in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--no-proxy-server"]:
    options.add_argument(flag)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 40)


def authenticator():
    return driver.execute_cdp_cmd("WebAuthn.addVirtualAuthenticator", {"options": {
        "protocol": "ctap2", "transport": "usb", "hasResidentKey": True,
        "hasUserVerification": True, "isUserVerified": True,
        "automaticPresenceSimulation": True,
    }})["authenticatorId"]


def credentials(key):
    return driver.execute_cdp_cmd("WebAuthn.getCredentials", {"authenticatorId": key})["credentials"]


def wait_file(path):
    limit = time.monotonic() + 180
    while not Path(path).exists():
        if time.monotonic() > limit:
            raise AssertionError("test coordination timed out")
        time.sleep(0.25)


def register(label):
    button = wait.until(EC.element_to_be_clickable((By.ID, "registerWebAuthn")))
    button.click()
    # Keycloak prompts for the friendly label after the browser returns the
    # WebAuthn assertion. This is synthetic browser UI, not a real authenticator.
    alert = wait.until(EC.alert_is_present())
    alert.send_keys(label)
    alert.accept()


def exchange(verifier, state):
    assert callback["state"] == [state]
    form = urllib.parse.urlencode({
        "client_id": "kaiba-ssh", "grant_type": "authorization_code", "code": callback["code"][0],
        "redirect_uri": "http://127.0.0.1:8400", "code_verifier": verifier,
    }).encode()
    with urllib.request.urlopen(origin + "/realms/kaiba/protocol/openid-connect/token", data=form) as response:
        tokens = json.load(response)
    assert "refresh_token" not in tokens
    payload = tokens["id_token"].split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return tokens["id_token"], claims


def issue(id_token):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    body = json.dumps({"publicKey": public_key.decode().split()[1], "ott": id_token}).encode()
    request = urllib.request.Request(origin + "/ssh/sign", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)["crt"]


def authorize(action=None):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    query = {
        "client_id": "kaiba-ssh", "response_type": "code", "scope": "openid profile email",
        "redirect_uri": "http://127.0.0.1:8400", "state": state, "nonce": secrets.token_urlsafe(16),
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    if action:
        query["kc_action"] = action
    driver.get(origin + "/realms/kaiba/protocol/openid-connect/auth?" + urllib.parse.urlencode(query))
    # Some Keycloak themes automatically trigger discovery; others expose a
    # button. A passkey-only flow must never expose a password field.
    assert not driver.find_elements(By.CSS_SELECTOR, "input[type=password]")
    for button in driver.find_elements(By.ID, "authenticateWebAuthnButton"):
        button.click()
    return verifier, state


try:
    driver.execute_cdp_cmd("WebAuthn.enable", {})
    first = authenticator()
    driver.get(fixture["url"])
    username = wait.until(EC.presence_of_element_located((By.ID, "username")))
    username.clear()
    username.send_keys("owner")
    driver.find_element(By.ID, "password").send_keys(fixture["password"])
    driver.find_element(By.ID, "kc-login").click()
    register("Synthetic test passkey one")
    wait.until(lambda _: len(credentials(first)) == 1)
    # Registration submission and its persistence finish before the test asks
    # the server to evaluate the single-key rejection.
    wait.until(lambda _: not driver.find_elements(By.ID, "registerWebAuthn"))
    Path("/tmp/first-passkey-ready").touch()
    wait_file("/tmp/register-second")
    pre_verifier, pre_state = authorize("webauthn-register-passwordless")
    wait.until(EC.presence_of_element_located((By.ID, "registerWebAuthn")))
    first_credentials = credentials(first)
    driver.execute_cdp_cmd("WebAuthn.removeVirtualAuthenticator", {"authenticatorId": first})
    second = authenticator()
    register("Synthetic test passkey two")
    wait.until(lambda _: len(credentials(second)) == 1)
    wait.until(lambda _: "code" in callback)
    pre_token, pre_claims = exchange(pre_verifier, pre_state)
    assert "kaiba-ssh-admin" not in pre_claims.get("groups", [])
    try:
        issue(pre_token)
        raise AssertionError("CA issued SSH access before owner finalization")
    except urllib.error.HTTPError as error:
        assert error.code in {401, 403}
    Path("/tmp/second-passkey-ready").touch()
    wait_file("/tmp/owner-finalized")
    callback.clear()
    driver.delete_all_cookies()
    verifier, state = authorize()
    wait.until(lambda _: "code" in callback)
    id_token, claims = exchange(verifier, state)
    assert claims["iss"] == origin + "/realms/kaiba"
    assert claims["aud"] == "kaiba-ssh"
    assert claims["preferred_username"] == "owner"
    assert claims["groups"] == ["kaiba-ssh-admin"]
    encoded = issue(id_token)
    certificate = serialization.load_ssh_public_identity(b"ssh-ed25519-cert-v01@openssh.com " + encoded.encode())
    certificate.verify_cert_signature()
    expected_ca = serialization.load_ssh_public_key(fixture["ssh_ca_public_key"].encode())
    raw = lambda key: key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw(certificate.signature_key()) == raw(expected_ca)
    assert certificate.valid_principals == [("kaiba:person:" + claims["sub"]).encode()]
    assert certificate.key_id == (claims["iss"] + "#" + claims["sub"]).encode()
    assert certificate.type == serialization.SSHCertificateType.USER
    assert 8 * 3600 <= certificate.valid_before - certificate.valid_after <= 8 * 3600 + 60
    assert certificate.extensions == {b"permit-pty": b""}
    server.shutdown()
    server.server_close()
    from client_flow import exercise_client
    ssh_ca_blob = base64.b64decode(fixture["ssh_ca_public_key"].split()[1])
    exercise_client(driver, {
        "caURL": origin,
        "rootFingerprint": fixture["rootFingerprint"],
        "sshUserCAFingerprint": "SHA256:" + base64.b64encode(hashlib.sha256(ssh_ca_blob).digest()).decode().rstrip("="),
        "issuer": claims["iss"], "clientID": "kaiba-ssh",
        "principal": "kaiba:person:" + claims["sub"],
    })
    Path("/tmp/passkey-login-success").touch()
    print("Two virtual passkeys registered; fresh passkey login, S256 code exchange and real SSH certificate issuance succeeded.")
except Exception:
    Path("/tmp/browser-flow-failed").touch()
    print("Last page URL path:", urllib.parse.urlsplit(driver.current_url).path)
    print(driver.page_source)
    traceback.print_exc()
    raise
finally:
    driver.quit()
    server.shutdown()
    server.server_close()
