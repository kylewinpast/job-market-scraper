"""US job board scraper: Ashby public job-board API (no API key needed).

GET https://api.ashbyhq.com/posting-api/job-board/{boardName} returns
{"jobs": [...]}. Same output schema as us_boards.py so ghost.py /
analyze.py keep working. US-only filtering reuses us_boards heuristics.
"""
import json
import time
import urllib.request

from us_boards import is_data_role, is_us_relevant, html_to_text

HEADERS = {"User-Agent": "job-market-scraper/0.1 (personal portfolio project)"}

# (ashby_board_name, company label). Verified working via probe 2026-09-26
# (HTTP 200 + non-empty + >=30% US postings, real `location` field).
BOARDS = [
    ("linear", "Linear"),
    ("ramp", "Ramp"),
    ("cursor", "Cursor"),
    ("notion", "Notion"),
    ("perplexity", "Perplexity"),
    ("harvey", "Harvey"),
    ("openai", "OpenAI"),
    ("benchling", "Benchling"),
    ("plaid", "Plaid"),
    ("kalshi", "Kalshi"),
    ("polymarket", "Polymarket"),
    ("abridge", "Abridge"),
    ("cohere", "Cohere"),
    ("clickhouse", "ClickHouse"),
    ("supabase", "Supabase"),
    ("resend", "Resend"),
    ("vanta", "Vanta"),
    ("drata", "Drata"),
    ("clickup", "ClickUp"),
    ("miro", "Miro"),
    ("sierra", "Sierra"),
]


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_board(board, label):
    payload = json.loads(http_get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board}"))
    results = []
    for j in payload.get("jobs", []):
        title = j.get("title") or ""
        if not is_data_role(title):
            continue
        loc = j.get("location") or ""
        if not is_us_relevant(loc):
            continue
        etype = (j.get("employmentType") or "").lower()
        job_type = {"fulltime": "Full-time", "parttime": "Part-time",
                    "contract": "Contract", "internship": "Internship",
                    "temporary": "Temporary"}.get(etype)
        results.append({
            "source": f"ashby-{board}",
            "external_id": str(j.get("id")),
            "title": title,
            "company": label,
            "location": loc,
            "job_type": job_type,
            "category": j.get("department"),
            "salary": None,
            "description": j.get("descriptionPlain") or html_to_text(
                j.get("descriptionHtml")),
            "url": j.get("jobUrl") or j.get("applyUrl"),
            "posted_at": j.get("publishedAt"),
        })
    return results


def fetch_ashby_boards():
    """Zero-arg entry point for scraper.py's fetcher list."""
    all_jobs = []
    for board, label in BOARDS:
        try:
            jobs = fetch_board(board, label)
            print(f"ashby/{board}: {len(jobs)} US data-role postings")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"ashby/{board} failed: {e}")
        time.sleep(2)
    return all_jobs


if __name__ == "__main__":
    jobs = fetch_ashby_boards()
    print(f"total: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  [{j['company']}] {j['title']} ({j['location']})")
