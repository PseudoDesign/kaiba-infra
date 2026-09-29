"""Run step-ca while withholding its bearer-token log fields from the journal."""
import json
import re
import signal
import subprocess
import sys

JWT = re.compile(r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()
                if key.lower() not in {"ott", "token", "authorization", "id_token", "access_token", "refresh_token"}}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return JWT.sub("[redacted bearer token]", value)
    return value


def main():
    child = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    def stop(signum, _frame):
        if child.poll() is None:
            child.send_signal(signum)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for line in child.stdout:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            value = {"message": line.rstrip()}
        print(json.dumps(redact(value)), flush=True)
    return child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
