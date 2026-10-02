#!/usr/bin/env python3
"""Inventory, import, and reconcile the explicitly listed Kaiba repositories.

Imports never overwrite an existing repository, enable Actions, or change the
GitHub source. Credentials stay in memory; errors omit HTTP bodies and tokens.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SLUG = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def private_read(path):
    with open(path, opener=lambda p, flags: os.open(p, flags | os.O_NOFOLLOW)) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError("credential must be a private regular file")
        value = handle.read(65537).strip()
    if not value or len(value) > 65536 or any(c.isspace() for c in value):
        raise ValueError("invalid credential")
    return value


def manifest(path):
    value = json.loads(Path(path).read_text())
    if value.get("schema_version") != "kaiba.forgejo-projects/v1":
        raise ValueError("unknown migration inventory schema")
    url = urllib.parse.urlsplit(value["forge_url"])
    if url.scheme != "https" or url.netloc != "git.pseudo.design" or url.path or url.query or url.fragment:
        raise ValueError("unexpected forge origin")
    rows = value["repositories"]
    if not rows or len({r["destination"] for r in rows}) != len(rows):
        raise ValueError("empty or duplicated inventory")
    for row in rows:
        if (not SLUG.fullmatch(row["source"]) or not SLUG.fullmatch(row["destination"])
                or type(row["private"]) is not bool):
            raise ValueError("invalid repository inventory")
    return value


def github(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError("GitHub inventory request failed: " + path.split("?")[0])
    return json.loads(result.stdout)


def github_list(path):
    rows = []
    sep = "&" if "?" in path else "?"
    for page in range(1, 1001):
        items = github(f"{path}{sep}per_page=100&page={page}")
        if not isinstance(items, list):
            raise ValueError("expected GitHub list")
        rows.extend(items)
        if len(items) < 100:
            return rows
    raise RuntimeError("GitHub pagination did not finish")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("forge API redirected unexpectedly")


class Forge:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, value=None):
        if not path.startswith("/") or path.startswith("//") or ".." in path:
            raise ValueError("invalid forge API path")
        request = urllib.request.Request(self.url + "/api/v1" + path,
            data=None if value is None else json.dumps(value).encode(), method=method,
            headers={"Authorization": "token " + self.token, "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=1800) as response:
                body = response.read(64 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == "GET":
                return None
            raise RuntimeError(f"forge API returned HTTP {error.code}") from None
        if len(body) > 64 * 1024 * 1024:
            raise RuntimeError("forge API response too large")
        return json.loads(body) if body else None


def inventory(row):
    slug = row["source"]
    repo = github("repos/" + slug)
    if repo["full_name"] != slug or repo["private"] != row["private"]:
        raise ValueError("source identity or visibility differs from inventory")
    result = {"source": slug, "destination": row["destination"], "repository": repo}
    for name, path in {
        "branches": "/branches", "tags": "/tags", "issues": "/issues?state=all",
        "pull_requests": "/pulls?state=all", "labels": "/labels", "milestones": "/milestones?state=all",
        "releases": "/releases", "comments": "/issues/comments", "reviews_comments": "/pulls/comments",
    }.items():
        result[name] = github_list("repos/" + slug + path)
    result["reviews"] = {str(pr["number"]): github_list(f'repos/{slug}/pulls/{pr["number"]}/reviews')
        for pr in result["pull_requests"]}
    result["workflows"] = github("repos/" + slug + "/actions/workflows")
    result["source_refs"] = git_refs("https://github.com/" + slug + ".git")
    return result


def git_refs(url, forge_token=None):
    # gh's credential helper supplies private GitHub credentials without URL tokens.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    options = ["-c", "credential.helper=", "-c", "http.followRedirects=false",
        "-c", "credential.https://github.com.helper=!gh auth git-credential"]
    if forge_token:
        env["KAIBA_FORGEJO_GIT_TOKEN"] = forge_token
        helper = "!python3 " + str(Path(__file__).with_name("forgejo_git_credential.py"))
        options += ["-c", "credential.https://git.pseudo.design.helper=" + helper]
    result = subprocess.run(["git", *options,
        "ls-remote", "--heads", "--tags", url], capture_output=True, text=True, timeout=120,
        env=env)
    if result.returncode:
        raise RuntimeError("cannot read Git refs")
    return dict((ref, sha) for sha, ref in (line.split() for line in result.stdout.splitlines()))


def import_repo(forge, row, source_token):
    if forge.request("GET", "/repos/" + row["destination"]) is not None:
        raise RuntimeError("destination already exists; refusing to overwrite")
    source = github("repos/" + row["source"])
    if source["full_name"] != row["source"] or source["private"] != row["private"]:
        raise ValueError("source visibility changed")
    owner, name = row["destination"].split("/")
    result = forge.request("POST", "/repos/migrate", {
        "clone_addr": "https://github.com/" + row["source"] + ".git",
        "auth_token": source_token, "repo_owner": owner, "repo_name": name,
        "service": "github", "private": row["private"], "mirror": False,
        "issues": True, "pull_requests": True, "labels": True, "milestones": True,
        "releases": True, "wiki": True, "lfs": True,
    })
    if result is None or result.get("full_name") != row["destination"] or result.get("private") != row["private"]:
        raise RuntimeError("import readback differs from requested identity/visibility")
    # Explicitly keep execution disabled while imported YAML is unreviewed.
    forge.request("PATCH", "/repos/" + row["destination"], {"has_actions": False})
    return {"source": row["source"], "destination": row["destination"], "imported": True,
        "authoritative": False, "verified": False}


def compare_refs(source, destination):
    return {"missing": sorted(set(source) - set(destination)),
        "unexpected": sorted(set(destination) - set(source)),
        "changed": sorted(ref for ref in source.keys() & destination.keys() if source[ref] != destination[ref])}


def forge_list(forge, path):
    rows = []
    separator = "&" if "?" in path else "?"
    for page in range(1, 1001):
        items = forge.request("GET", f"{path}{separator}limit=50&page={page}")
        if not isinstance(items, list):
            raise ValueError("unexpected Forgejo inventory list")
        rows.extend(items)
        if len(items) < 50:
            return rows
    raise RuntimeError("Forgejo pagination did not finish")


def compare_records(source, destination, key, fields):
    before = {str(item[key]): item for item in source}
    after = {str(item[key]): item for item in destination}
    if len(before) != len(source) or len(after) != len(destination):
        raise ValueError("duplicate migration record identity")
    return {"missing": sorted(before.keys() - after.keys()),
        "unexpected": sorted(after.keys() - before.keys()),
        "changed": {identity: [field for field in fields if before[identity].get(field) != after[identity].get(field)]
            for identity in sorted(before.keys() & after.keys())
            if any(before[identity].get(field) != after[identity].get(field) for field in fields)}}


def verify_metadata(forge, row, snapshot):
    if snapshot.get("source") != row["source"] or snapshot.get("destination") != row["destination"]:
        raise ValueError("inventory snapshot belongs to a different repository")
    root = "/repos/" + row["destination"]
    issues = [item for item in snapshot["issues"] if "pull_request" not in item]
    # Number/title/body/state are portable. Author identity, review events,
    # workflow logs and project boards require archive/manual reconciliation.
    specs = {
        "issues": (issues, "/issues?state=all&type=issues", "number", ("title", "body", "state")),
        "pull_requests": (snapshot["pull_requests"], "/pulls?state=all", "number", ("title", "body", "state", "merged_at")),
        "labels": (snapshot["labels"], "/labels", "name", ("color", "description")),
        "milestones": (snapshot["milestones"], "/milestones?state=all", "title", ("description", "state")),
        "releases": (snapshot["releases"], "/releases", "tag_name", ("name", "body", "draft", "prerelease")),
    }
    result = {name: compare_records(source, forge_list(forge, root + path), key, fields)
        for name, (source, path, key, fields) in specs.items()}
    result["portable_metadata_match"] = not any(any(diff.values()) for diff in result.values())
    result["manual_reconciliation_required"] = ["comment/review authors and timestamps", "PR review history",
        "LFS object hashes", "wiki refs", "release asset hashes", "project boards", "Actions history and artifacts"]
    result["fully_verified"] = False
    return result


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory", "import", "verify", "verify-metadata"])
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("forgejo-projects.json")))
    parser.add_argument("--repo", required=True, help="Source slug from the explicit migration inventory")
    parser.add_argument("--output", required=True)
    parser.add_argument("--forge-token-file")
    parser.add_argument("--snapshot", help="Private source inventory JSON for metadata reconciliation")
    args = parser.parse_args()
    config = manifest(args.manifest)
    matches = [r for r in config["repositories"] if r["source"] == args.repo]
    if len(matches) != 1:
        raise ValueError("repository is outside the migration inventory")
    row = matches[0]
    if Path(args.output).exists():
        raise ValueError("output already exists")
    if args.command == "inventory":
        result = inventory(row)
    else:
        if not args.forge_token_file:
            raise ValueError("forge token file required")
        forge = Forge(config["forge_url"], private_read(args.forge_token_file))
        if args.command == "import":
            credential = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
            result = import_repo(forge, row, credential)
        elif args.command == "verify-metadata":
            if not args.snapshot:
                raise ValueError("source inventory snapshot required")
            result = verify_metadata(forge, row, json.loads(Path(args.snapshot).read_text()))
        else:
            destination = forge.request("GET", "/repos/" + row["destination"])
            if destination is None or destination.get("private") != row["private"]:
                raise RuntimeError("destination missing or visibility differs")
            # Public repos can be inspected directly; private refs require an
            # already-configured HTTPS credential helper (never put tokens in URLs).
            result = compare_refs(git_refs("https://github.com/" + row["source"] + ".git"),
                git_refs(config["forge_url"] + "/" + row["destination"] + ".git", forge.token))
            result["git_refs_match"] = not any(result.values())
    private_json(args.output, result)
    print(json.dumps({"repository": args.repo, "command": args.command, "output": args.output}))
    return 0 if result.get("git_refs_match", True) and result.get("portable_metadata_match", True) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, (ValueError, RuntimeError)) else "migration operation failed", file=sys.stderr)
        raise SystemExit(1)
