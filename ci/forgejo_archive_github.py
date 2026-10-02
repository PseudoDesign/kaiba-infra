#!/usr/bin/env python3
"""Encrypt available GitHub Actions artifacts and logs for the migration.

Downloads stream directly into age. Receipts distinguish archived bytes from
expired/unavailable history. Repository identities come from the allowlist;
credentials remain with gh and are never copied into an archive.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from forgejo_migrate import manifest, private_json


def file_sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(item, destination, recipients, age):
    slug, kind, identity, digest = item
    directory = destination / slug.replace("/", "--") / kind
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    output = directory / f"{identity}.zip.age"
    receipt = directory / f"{identity}.json"
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if previous.get("archived") and output.exists():
            actual = file_sha256(output)
            if actual != previous.get("ciphertext_sha256"):
                raise ValueError("existing archive hash differs")
            return previous
        # Unavailable downloads are retried on an explicitly repeated command.
        receipt.unlink()
    if output.exists():
        raise ValueError("archive without receipt; reconcile before retrying")
    path = f"repos/{slug}/actions/" + (f"artifacts/{identity}/zip" if kind == "artifacts" else f"runs/{identity}/logs")
    partial = directory / f".{identity}.partial"
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    result = {"source": slug, "kind": kind, "id": identity, "archived": False}
    try:
        with os.fdopen(fd, "wb") as encrypted:
            with subprocess.Popen(["gh", "api", path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as source:
                with subprocess.Popen([age, "-R", str(recipients)], stdin=subprocess.PIPE,
                        stdout=encrypted, stderr=subprocess.DEVNULL) as cipher:
                    checksum = hashlib.sha256()
                    size = 0
                    for chunk in iter(lambda: source.stdout.read(1024 * 1024), b""):
                        size += len(chunk)
                        if size > 2 * 1024**3:
                            source.terminate()
                            raise ValueError("Actions archive exceeds 2 GiB limit")
                        checksum.update(chunk)
                        cipher.stdin.write(chunk)
                    cipher.stdin.close()
                    cipher_status = cipher.wait(timeout=60)
                source_status = source.wait(timeout=60)
        if source_status or cipher_status or not size:
            result["unavailable"] = "Download unavailable with current credentials or retention; no bytes archived"
        elif digest and digest != "sha256:" + checksum.hexdigest():
            raise ValueError("GitHub artifact digest differs from downloaded bytes")
        else:
            partial.rename(output)
            result.update(archived=True, plaintext_sha256=checksum.hexdigest(), size_in_bytes=size,
                ciphertext_sha256=file_sha256(output),
                github_digest_verified=bool(digest), decryption_tested=False)
        private_json(receipt, result)
        return result
    finally:
        partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-directory", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--recipient-file", required=True, type=Path)
    parser.add_argument("--age", default="age")
    parser.add_argument("--logs", action="store_true")
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--limit", type=int, help="Bound a rehearsal to the first N available archives")
    args = parser.parse_args()
    os.umask(0o077)
    allowed = {row["source"] for row in manifest(Path(__file__).with_name("forgejo-projects.json"))["repositories"]}
    items = []
    for snapshot in sorted(args.snapshot_directory.glob("*-history.json")):
        value = json.loads(snapshot.read_text())
        slug = value["source"]
        if slug not in allowed:
            raise ValueError("archive repository outside migration inventory")
        history = value["unsupported_in_forgejo_import"]
        for artifact in history.get("action_artifacts", []):
            if artifact.get("expired"):
                continue
            identity = artifact["id"]
            if type(identity) is not int or identity <= 0:
                raise ValueError("invalid artifact identity")
            items.append((slug, "artifacts", identity, artifact.get("digest")))
        if args.logs:
            for run in history.get("action_runs", []):
                if run.get("status") != "completed":
                    continue
                identity = run["id"]
                if type(identity) is not int or identity <= 0:
                    raise ValueError("invalid workflow run identity")
                items.append((slug, "logs", identity, None))
    if len(set((s, k, i) for s, k, i, _ in items)) != len(items):
        raise ValueError("duplicate archive identity")
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("archive limit must be positive")
        items = items[:args.limit]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda item: download(item, args.destination, args.recipient_file, args.age), items):
            print(json.dumps({key: result[key] for key in ("source", "kind", "id", "archived")}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError):
        print("Actions archival failed; inspect receipts and retry without assuming completeness", file=sys.stderr)
        raise SystemExit(1)
