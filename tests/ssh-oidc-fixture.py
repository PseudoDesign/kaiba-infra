"""Ephemeral, deliberately unauthenticated OIDC issuer used only inside the test VM."""
import base64
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import ssl
import sys
import time
import uuid
import urllib.error
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import NameOID
import jwt

ISSUER = "https://oidc.test:9443"
SUBJECT = "3b227970-9feb-463a-98f2-4e165fa4ad3a"


def serve():
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key()))
    jwk.update(kid="test-only", use="sig", alg="RS256")
    tls_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "oidc.test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(tls_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1)).not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("oidc.test")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(tls_key, hashes.SHA256()))
    Path("/run/fixture-oidc.crt").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    Path("/run/fixture-oidc.key").write_bytes(tls_key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

    class Handler(BaseHTTPRequestHandler):
        def respond(self, value):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def do_GET(self):
            if self.path == "/.well-known/openid-configuration":
                self.respond({"issuer": ISSUER, "jwks_uri": ISSUER + "/jwks",
                    "authorization_endpoint": ISSUER + "/authorize", "token_endpoint": ISSUER + "/token",
                    "id_token_signing_alg_values_supported": ["RS256"], "response_types_supported": ["code"]})
            elif self.path == "/jwks":
                self.respond({"keys": [jwk]})
            else:
                self.send_error(404)

        def do_POST(self):
            claims = {"iss": ISSUER, "aud": "kaiba-ssh", "azp": "kaiba-ssh", "sub": SUBJECT,
                "iat": int(time.time()), "exp": int(time.time()) + 300, "nonce": str(uuid.uuid4()),
                "groups": ["kaiba-ssh-admin"]}
            claims.update(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.respond({"id_token": jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "test-only"})})

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 9443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("/run/fixture-oidc.crt", "/run/fixture-oidc.key")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


def verify():
    oidc_tls = ssl.create_default_context(cafile="/run/fixture-oidc.crt")
    ca_tls = ssl.create_default_context(cafile="/var/lib/kaiba-ssh-ca/root_ca.crt")
    key = ed25519.Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                              serialization.PublicFormat.OpenSSH).decode().split()[1]

    def post(url, body, context):
        request = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, context=context, timeout=10) as response:
            return json.load(response)

    def token(changes=None):
        return post(ISSUER + "/token", changes or {}, oidc_tls)["id_token"]

    def issue(claims=None, request=None, ott=None, endpoint="/ssh/sign"):
        body = {"ott": ott or token(claims), "publicKey": public_key}
        body.update(request or {})
        return post("https://localhost:8443" + endpoint, body, ca_tls)

    def denied(label, allowed_status=None, **kwargs):
        try:
            issue(**kwargs)
        except urllib.error.HTTPError as error:
            assert (error.code in allowed_status if allowed_status else 400 <= error.code < 500), (label, error.code, error.read())
        else:
            raise AssertionError("unauthorized request succeeded: " + label)

    encoded = issue()["crt"]
    certificate = serialization.load_ssh_public_identity(b"ssh-ed25519-cert-v01@openssh.com " + encoded.encode())
    certificate.verify_cert_signature()
    expected_ca = serialization.load_ssh_public_key(Path("/var/lib/kaiba-ssh-ca/ssh_user_ca.pub").read_bytes())
    raw_public = lambda value: value.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw_public(certificate.signature_key()) == raw_public(expected_ca)
    assert certificate.valid_principals == [("kaiba:person:" + SUBJECT).encode()]
    assert certificate.key_id == (ISSUER + "#" + SUBJECT).encode()
    assert certificate.type == serialization.SSHCertificateType.USER
    assert 8 * 3600 <= certificate.valid_before - certificate.valid_after <= 8 * 3600 + 60
    assert certificate.extensions == {b"permit-pty": b""}
    # Certificate remains independently verifiable after restarting the service.
    Path("/run/issued-cert.pub").write_bytes(b"ssh-ed25519-cert-v01@openssh.com " + encoded.encode() + b"\n")
    for label, changes in [
        ("wrong issuer", {"iss": "https://elsewhere.invalid"}),
        ("wrong audience", {"aud": "another-app"}),
        ("wrong authorized party", {"azp": "another-app"}),
        ("missing membership", {"groups": []}),
        ("other membership", {"groups": ["administrator"]}),
        ("missing subject", {"sub": ""}),
        ("unsafe subject", {"sub": "adam\nroot"}),
        ("expired token", {"exp": int(time.time()) - 120}),
    ]:
        denied(label, claims=changes)
    denied("requested root", request={"principals": ["root"]})
    denied("another person's principal", request={"principals": ["kaiba:person:another"]})
    denied("host certificate", request={"certType": "host"})
    denied("oversized lifetime", request={"validBefore": "9h"})
    denied("future eight-hour window", request={"validAfter": "720h", "validBefore": "728h"})
    denied("future default duration", request={"validAfter": "720h"})
    denied("excessive custom backdate", request={"validAfter": "-48h", "validBefore": "7h"})
    # A short explicit backdate is still supported for clock skew; the expiry
    # remains bounded by eight hours from issuance, not by that start time.
    skewed = issue(request={"validAfter": "-30s", "validBefore": "8h"})["crt"]
    skewed_certificate = serialization.load_ssh_public_identity(
        b"ssh-ed25519-cert-v01@openssh.com " + skewed.encode())
    assert skewed_certificate.valid_before <= int(time.time()) + 8 * 3600

    replay = token()
    issue(ott=replay)
    denied("replayed bearer token", ott=replay)
    # Existing user-key possession cannot renew/rekey the certificate. OIDC
    # deliberately does not implement these methods, and no SSHPOP provisioner
    # is configured. Exercise both a fresh OIDC token and a genuine proof signed
    # by the private key of the issued certificate (not malformed test input).
    for endpoint in ["/ssh/renew", "/ssh/rekey"]:
        denied("OIDC " + endpoint, allowed_status={401}, endpoint=endpoint)
        now = int(time.time())
        proof = jwt.encode({
            "iss": "kaiba-human", "sub": str(certificate.serial),
            "aud": "https://localhost:8443" + endpoint,
            "iat": now, "nbf": now, "exp": now + 300, "jti": str(uuid.uuid4()),
        }, key, algorithm="EdDSA", headers={"sshpop": encoded})
        denied("existing user certificate " + endpoint, allowed_status={401},
               endpoint=endpoint, ott=proof)
    # An authenticated OIDC user must not gain an unrelated X.509 identity.
    csr = (x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "unexpected-client")])).sign(key, None))
    denied("X.509 issuance", allowed_status={500}, endpoint="/sign", request={
        "csr": csr.public_bytes(serialization.Encoding.PEM).decode()})
    print("Real step-ca authorization and certificate validation passed")


if __name__ == "__main__":
    {"serve": serve, "verify": verify}[sys.argv[1]]()
