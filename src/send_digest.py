"""Send the Real Jobs Digest via the Resend API.

Setup (Kyle does this once):
  1. Create a free account at https://resend.com
  2. Verify a sending domain (or use Resend's test domain for trials)
  3. export RESEND_API_KEY="re_..." ALERT_RECIPIENTS="a@x.com,b@y.com"

Then:  python src/send_digest.py            # sends today's digest
       python src/send_digest.py --dry-run  # prints payload without sending
       python src/send_digest.py --subscribers data/subscribers.json
                                            # sends to every Buttondown subscriber

If RESEND_API_KEY is missing, this prints setup instructions and exits 0
so the daily pipeline never fails because of email config.
"""
import argparse
import json
import os
import sys
import urllib.request

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT, "output")

# Change this once the sending domain is verified in Resend.
FROM_ADDRESS = "Ghost Job Tracker <alerts@ghostjobtracker.com>"
RESEND_URL = "https://api.resend.com/emails"

SETUP_HELP = """\
Resend is not configured yet. To enable email digests:

  1. Create a free account at https://resend.com
  2. Verify your sending domain (Resend dashboard -> Domains),
     or use Resend's test domain for trials.
  3. Create an API key and export it:
       export RESEND_API_KEY="re_..."
       export ALERT_RECIPIENTS="you@example.com"

  Then run:  python src/send_digest.py --dry-run   (preview)
             python src/send_digest.py              (send)
"""


def load_digest(date):
    html_path = os.path.join(OUT_DIR, f"digest_{date}.html")
    text_path = os.path.join(OUT_DIR, f"digest_{date}.txt")
    if not os.path.exists(html_path):
        print(f"error: {html_path} not found — run src/alerts.py first",
              file=sys.stderr)
        sys.exit(2)
    with open(html_path, encoding="utf-8") as f:
        html_body = f.read()
    with open(text_path, encoding="utf-8") as f:
        text_body = f.read()
    return html_body, text_body


def job_count(date):
    path = os.path.join(PROJECT, "data", f"alerts_{date}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["count"]
    except (OSError, KeyError, ValueError):
        return None


def load_subscriber_emails(path):
    """Load a subscriber email list from JSON (list of str or list of dicts)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    emails = []
    for item in data if isinstance(data, list) else []:
        email = item.get("email") if isinstance(item, dict) else item
        email = (email or "").strip()
        if email and "@" in email and email not in emails:
            emails.append(email)
    return emails


def send(api_key, payload):
    req = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description="Send the Real Jobs Digest email")
    ap.add_argument("--date", help="digest date YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--to", help="comma-separated recipients (overrides ALERT_RECIPIENTS)")
    ap.add_argument("--subscribers",
                    help="JSON file with the subscriber list "
                         "(e.g. data/subscribers.json from src/sync_subscribers.py); "
                         "sends the digest to every address in it")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the payload without sending")
    args = ap.parse_args()

    from datetime import datetime, timezone
    date = args.date or datetime.now(timezone.utc).date().isoformat()

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if args.subscribers:
        try:
            to_list = load_subscriber_emails(args.subscribers)
        except (OSError, ValueError) as e:
            print(f"error: cannot load subscriber list: {e}", file=sys.stderr)
            return 2
        if not to_list:
            print("no subscribers — nothing to send")
            return 0
    else:
        recipients = (args.to or os.environ.get("ALERT_RECIPIENTS", "")).strip()
        to_list = [a.strip() for a in recipients.split(",") if a.strip()]

    if args.dry_run:
        html_body, text_body = load_digest(date)
        n = job_count(date)
        subject = (f"{n} real new jobs today — zero ghosts ({date})"
                   if n is not None else f"Real Jobs Digest ({date})")
        print(f"[dry-run] from: {FROM_ADDRESS}")
        print(f"[dry-run] to: {', '.join(to_list) or '(no recipients configured)'}")
        print(f"[dry-run] subject: {subject}")
        print(f"[dry-run] html bytes: {len(html_body):,}, "
              f"text bytes: {len(text_body):,}")
        return 0

    if not api_key:
        print(SETUP_HELP)
        return 0

    if not to_list:
        print("error: no recipients — set ALERT_RECIPIENTS or pass --to",
              file=sys.stderr)
        return 2

    html_body, text_body = load_digest(date)
    n = job_count(date)
    subject = (f"{n} real new jobs today — zero ghosts ({date})"
               if n is not None else f"Real Jobs Digest ({date})")

    payload = {"from": FROM_ADDRESS, "to": to_list,
               "subject": subject, "html": html_body, "text": text_body}

    status, resp = send(api_key, payload)
    print(f"sent digest {date} to {len(to_list)} recipient(s): "
          f"HTTP {status}, id={resp.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
