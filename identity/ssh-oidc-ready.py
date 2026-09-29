"""Require usable, TLS-verified OIDC discovery before starting step-ca.

step-ca can otherwise remain running with its OIDC provisioner disabled after
an initialization failure. Let systemd retry startup while the issuer or its
public TLS certificate is not ready. This process has no login credentials.
"""
import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise ValueError("OIDC discovery and JWKS URLs must not redirect")


def check(issuer, trust_bundle):
    context = ssl.create_default_context(cafile=trust_bundle)
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), NoRedirect())

    def document(url):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.fragment):
            raise ValueError("OIDC metadata URLs must use HTTPS without credentials or fragments")
        with opener.open(url, timeout=10) as response:
            body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError("OIDC metadata exceeds the size limit")
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError("OIDC metadata must be an object")
        return result

    discovery = document(issuer + "/.well-known/openid-configuration")
    if discovery.get("issuer") != issuer:
        raise ValueError("OIDC discovery issuer does not match the configured issuer")
    jwks_url = discovery.get("jwks_uri")
    if not isinstance(jwks_url, str):
        raise ValueError("OIDC discovery has no JWKS URL")
    keys = document(jwks_url).get("keys")
    if not isinstance(keys, list) or not keys or not all(
            isinstance(key, dict) and key.get("kty") for key in keys):
        raise ValueError("OIDC JWKS has no usable key set")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--trust-bundle", required=True)
    args = parser.parse_args()
    try:
        check(args.issuer, args.trust_bundle)
    except (OSError, ValueError) as error:
        print("OIDC discovery is not ready: " + str(error), file=sys.stderr)
        sys.exit(1)
