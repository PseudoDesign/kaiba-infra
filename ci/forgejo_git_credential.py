#!/usr/bin/env python3
"""Ephemeral Git helper: emit credentials only to the configured forge origin."""
import os
import sys


def credential(fields, token):
    if fields.get("protocol") != "https" or fields.get("host") != "git.pseudo.design" or not token:
        return ""
    return "username=forge-recovery\npassword=" + token + "\n\n"


if __name__ == "__main__" and sys.argv[1:] == ["get"]:
    fields = dict(line.rstrip("\n").split("=", 1) for line in sys.stdin if "=" in line)
    sys.stdout.write(credential(fields, os.environ.get("KAIBA_FORGEJO_GIT_TOKEN", "")))
