"""Sync the Buttondown subscriber list into data/subscribers.json.

Runs the buttondown skill CLI (bin/bd_subscribers.py --out). Graceful
failure: if the Buttondown credential isn't connected yet, prints a clear
setup hint and exits 0 so the daily pipeline never breaks over email config.
"""
import os
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_CLI = os.path.expanduser(
    "~/workspace/skills/buttondown/bin/bd_subscribers.py")
OUT_PATH = os.path.join(PROJECT, "data", "subscribers.json")

SETUP_HINT = """\
Subscriber sync skipped: Buttondown is not connected yet.

To enable it:
  1. Create a free newsletter at https://buttondown.email and note your
     username (used in the site signup form).
  2. Get an API key from Buttondown -> Settings -> API and connect it
     via the secure connector as custom.buttondown.
  3. Re-run:  python src/sync_subscribers.py

Until then the signup form still works (it posts to Buttondown's public
embed endpoint) — only this automated sync stays off.
"""


def main():
    if not os.path.isfile(SKILL_CLI):
        print(f"skip: buttondown skill CLI not found at {SKILL_CLI}")
        return 0

    proc = subprocess.run(
        [sys.executable, SKILL_CLI, "--out", OUT_PATH],
        capture_output=True, text=True, timeout=120)
    out = (proc.stdout or "").strip()
    if out:
        print(out)

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if "not connected" in err.lower() or "credentials are not available" in err.lower():
            print(SETUP_HINT)
            return 0
        print(f"subscriber sync failed (exit {proc.returncode}): {err}",
              file=sys.stderr)
        return 0  # never break the daily pipeline over email config

    return 0


if __name__ == "__main__":
    sys.exit(main())
