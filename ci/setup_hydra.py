#!/usr/bin/env python3
"""Reconcile the two main-branch Hydra jobsets; preview unless --apply is given."""

import argparse
import getpass
import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Hydra's latest-finished endpoint redirects to a build. Only follow
        # reads within the same origin. Login's 302 becomes a GET without a body.
        source, target = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        login_redirect = (req.get_method() == "POST" and source.path == "/login"
                          and code == 302 and target.path == "/current-user")
        if (req.get_method() == "GET" or login_redirect) and (source.scheme, source.netloc) == (target.scheme, target.netloc):
            return super().redirect_request(req, fp, code, msg, headers, newurl)
        return None


class Hydra:
    def __init__(self, url):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" and not (
                parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"))):
            raise ValueError("use HTTPS, or HTTP over a local SSH tunnel")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("URL must be a server origin without credentials or a path")
        self.url = url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), SafeRedirect())

    def request(self, method, path, data=None):
        request = urllib.request.Request(
            self.url + path,
            data=None if data is None else json.dumps(data).encode(),
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json",
                     "Origin": self.url, "Referer": self.url + "/"})
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if method == "GET" and exc.code == 404:
                return None
            # Server error bodies can contain credentials; report status only.
            raise RuntimeError(f"Hydra {method} {path} returned HTTP {exc.code}") from None

    def reconcile(self, changes):
        for path, desired in changes:
            current = self.request("GET", path)
            expected = {key: value for key, value in desired.items() if key != "visible"}
            # Project and jobset serializers expose different visibility keys.
            if path.startswith("/project/"):
                expected["hidden"] = 0
            else:
                expected["visible"] = 1
            if current is None or any(current.get(key) != value for key, value in expected.items()):
                self.request("PUT", path, desired)
            current = self.request("GET", path)
            for key, value in expected.items():
                if current is None or current.get(key) != value:
                    raise RuntimeError(f"Hydra readback differs for {path}: {key}")
            print(f"Configured {path}")


def changes(definitions, stage):
    result = []
    for project, definition in definitions.items():
        if project not in ("kaiba-infra", "kaiba-provisioning"):
            raise ValueError(f"unexpected project: {project}")
        result.append((f"/project/{project}", {
            "name": project, "displayname": project,
            "description": definition["description"],
            "homepage": f"https://github.com/PseudoDesign/{project}",
            "enabled": 1, "visible": 1,
        }))
        result.append((f"/jobset/{project}/main", {
            "name": "main", "description": definition["description"],
            "type": 1, "flake": definition["flake"], "visible": 1,
            "enabled": int(project == "kaiba-infra" or stage == "provisioning"),
            "checkinterval": 300, "schedulingshares": 1, "keepnr": 3,
        }))
    if set(definitions) != {"kaiba-infra", "kaiba-provisioning"}:
        raise ValueError("both Kaiba projects must be configured")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://hydra.pseudo.design")
    parser.add_argument("--definitions", type=Path, default=Path(__file__).with_name("hydra-jobsets.json"))
    parser.add_argument("--stage", choices=("infrastructure", "provisioning"), default="infrastructure",
                        help="provisioning requires completed Ace qualification and a successful infrastructure build")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--username", default="adam")
    parser.add_argument("--password-file", type=Path, help="runtime secret file; otherwise prompt without echo")
    args = parser.parse_args(argv)
    try:
        desired = changes(json.loads(args.definitions.read_text()), args.stage)
        client = Hydra(args.url)
        if not args.apply:
            print(json.dumps(dict(desired), indent=2))
            return 0
        password = (args.password_file.read_text().rstrip("\n") if args.password_file
                    else getpass.getpass("Hydra administrator password: "))
        client.request("POST", "/login", {"username": args.username, "password": password})
        if args.stage == "provisioning":
            build = client.request("GET", "/job/kaiba-infra/main/aarch64-linux.selector/latest-finished")
            if not build or build.get("buildstatus") != 0 or build.get("finished") != 1:
                raise RuntimeError("provisioning requires a successful latest infrastructure build")
        client.reconcile(desired)
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Hydra setup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
