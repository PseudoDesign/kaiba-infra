"""Integration assertions against the live synthetic VM realm."""
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.error
import urllib.request

from keycloak_admin import Admin

for path in [
    "/admin/", "/realms/master/", "/realms/master/protocol/openid-connect/token",
    "/realms/kaiba/../master/", "/realms/kaiba/%2e%2e/master/",
    "/realms/kaiba/..;/master/", "/realms/kaiba/%252e%252e/master/",
    "/resources/../admin/", "/realms/kaiba;other/",
]:
    try:
        urllib.request.urlopen("https://acme.test" + path)
        raise AssertionError("private identity route exposed: " + path)
    except urllib.error.HTTPError as error:
        assert error.code in {400, 404}, (path, error.code)

admin = Admin("http://127.0.0.1:8080", "kaiba-bootstrap-admin", "test-only-identity-bootstrap", "kaiba")
realm = admin.api("GET")
assert not realm["registrationAllowed"] and not realm["resetPasswordAllowed"]
assert realm["webAuthnPolicyPasswordlessUserVerificationRequirement"] == "required"
assert realm["webAuthnPolicyPasswordlessRequireResidentKey"] == "Yes"
assert realm["browserFlow"] == "kaiba-passkey-only-v1"
ssh = admin.client("kaiba-ssh")
assert ssh["publicClient"] and ssh["standardFlowEnabled"]
assert not ssh["directAccessGrantsEnabled"] and not ssh["implicitFlowEnabled"]
assert not ssh["serviceAccountsEnabled"]
assert not admin.client("admin-cli")["directAccessGrantsEnabled"]
assert ssh["redirectUris"] == ["http://127.0.0.1:8400"]
assert ssh["attributes"]["pkce.code.challenge.method"] == "S256"
assert ssh["attributes"]["use.refresh.tokens"] == "false"
assert ssh["attributes"]["oauth2.device.authorization.grant.enabled"] == "false"
assert not admin.api("GET", "/clients/" + ssh["id"] + "/optional-client-scopes")
assert sorted(ssh["defaultClientScopes"]) == ["basic", "email", "profile"]
assert not admin.api("GET", "/default-optional-client-scopes")
# These protocol failures test effective policy, rather than only JSON shape.
base = "http://127.0.0.1:8080/realms/kaiba/protocol/openid-connect/"
for suffix, form in [
    ("token", {"client_id": "kaiba-ssh", "grant_type": "password", "username": "owner", "password": "wrong"}),
    ("auth/device", {"client_id": "kaiba-ssh", "scope": "openid"}),
]:
    request = urllib.request.Request(base + suffix, data=urllib.parse.urlencode(form).encode(), headers={"X-Forwarded-Proto": "https"})
    try:
        urllib.request.urlopen(request)
        raise AssertionError("forbidden grant was accepted")
    except urllib.error.HTTPError as error:
        assert error.code == 400
        assert json.loads(error.read())["error"] == "unauthorized_client"
class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(RejectRedirects())
for change in [
    {},  # A code request without PKCE must fail.
    {"code_challenge": "A" * 43, "code_challenge_method": "plain"},
    {"redirect_uri": "http://127.0.0.1:8401", "code_challenge": "A" * 43, "code_challenge_method": "S256"},
]:
    params = {"client_id": "kaiba-ssh", "response_type": "code", "scope": "openid",
        "redirect_uri": "http://127.0.0.1:8400"}
    params.update(change)
    request = urllib.request.Request(base + "auth?" + urllib.parse.urlencode(params), headers={"X-Forwarded-Proto": "https"})
    try:
        opener.open(request)
        raise AssertionError("invalid OAuth request reached an authentication flow")
    except urllib.error.HTTPError as error:
        assert error.code in {302, 400}
        if error.code == 302:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(error.headers["Location"]).query)
            assert "error" in query and "code" not in query

if "--enrolled" in sys.argv:
    users = admin.api("GET", "/users?exact=true&username=owner")
    assert len(users) == 1
    user_id = users[0]["id"]
    credentials = admin.api("GET", "/users/" + user_id + "/credentials")
    assert len([entry for entry in credentials if entry["type"] == "webauthn-passwordless"]) == 2
    assert not any(entry["type"] == "password" for entry in credentials)
    assert not admin.client("kaiba-owner-enrollment")["enabled"]
    assert [entry["name"] for entry in admin.api("GET", "/users/" + user_id + "/groups")] == ["kaiba-ssh-admin"]
    assert not Path("/var/lib/kaiba-human-identity/owner-enrollment-password").exists()
print("Effective Kaiba realm policy assertions passed.")
