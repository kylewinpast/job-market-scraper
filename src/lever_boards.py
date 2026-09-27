"""US job board scraper: Lever public postings API (no API key needed).

GET https://api.lever.co/v0/postings/{company}?mode=json returns a JSON array.
Same output schema as us_boards.py so ghost.py / analyze.py keep working.
US-only filtering reuses the shared heuristics from us_boards.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone

from us_boards import is_data_role, is_us_relevant, html_to_text

HEADERS = {"User-Agent": "job-market-scraper/0.1 (personal portfolio project)"}

# (lever_company_slug, company label). Verified working via probe 2026-09-26
# (HTTP 200 + non-empty + >=30% US postings).
BOARDS = [
    ("palantir", "Palantir"),
    ("ro", "Ro"),  # ro.co, healthcare tech
]


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_board(slug, label, retries=1):
    try:
        postings = json.loads(http_get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json"))
    except TimeoutError:
        if retries <= 0:
            raise
        time.sleep(5)
        return fetch_board(slug, label, retries - 1)
    results = []
    for p in postings:
        title = p.get("text") or ""
        if not is_data_role(title):
            continue
        cats = p.get("categories") or {}
        loc = cats.get("location") or ""
        if not is_us_relevant(loc):
            continue
        created = p.get("createdAt")
        posted = None
        if created:
            try:
                posted = datetime.fromtimestamp(int(created) / 1000,
                                                tz=timezone.utc).isoformat()
            except (ValueError, TypeError):
                posted = None
        results.append({
            "source": f"lever-{slug}",
            "external_id": str(p.get("id")),
            "title": title,
            "company": label,
            "location": loc,
            "job_type": cats.get("commitment"),
            "category": cats.get("team") or cats.get("department"),
            "salary": None,
            "description": p.get("descriptionPlain") or html_to_text(
                p.get("description")),
            "url": p.get("hostedUrl") or p.get("applyUrl"),
            "posted_at": posted,
        })
    return results


def fetch_lever_boards():
    """Zero-arg entry point for scraper.py's fetcher list."""
    all_jobs = []
    for slug, label in BOARDS:
        try:
            jobs = fetch_board(slug, label)
            print(f"lever/{slug}: {len(jobs)} US data-role postings")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"lever/{slug} failed: {e}")
        time.sleep(2)
    return all_jobs


if __name__ == "__main__":
    jobs = fetch_lever_boards()
    print(f"total: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  [{j['company']}] {j['title']} ({j['location']})")
