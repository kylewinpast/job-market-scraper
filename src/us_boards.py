"""US job board scraper: Greenhouse public Boards API (no API key needed).

Fetches data-role postings from US tech companies with NYC / remote-US
presence. Complements the EU-remote sources (Remotive, Arbeitnow) in
scraper.py so the dashboard actually covers Kyle's target markets
(DFW + US East Coast).

Strategy (to keep it fast): list jobs with content=false, filter to
data-role titles, then fetch full descriptions only for those.
"""
import html
import json
import re
import time
import urllib.request

HEADERS = {"User-Agent": "job-market-scraper/0.1 (personal portfolio project)"}

# (board_token, company label). All verified working 2026-09-26.
BOARDS = [
    ("datadog", "Datadog"),      # NYC HQ
    ("mongodb", "MongoDB"),      # NYC HQ
    ("robinhood", "Robinhood"),  # NYC office
    ("stripe", "Stripe"),        # NYC office
    ("coinbase", "Coinbase"),    # NYC / remote-US
    ("airbnb", "Airbnb"),        # NYC office
    ("lyft", "Lyft"),            # NYC office
    ("dropbox", "Dropbox"),
    ("figma", "Figma"),          # NYC office
    ("reddit", "Reddit"),        # NYC office
]

# Drop EMEA/APAC postings; US companies post mostly US roles anyway.
NON_US = ["france", "germany", "united kingdom", " ireland", "spain",
          "netherlands", "belgium", "sweden", "poland", "portugal",
          "italy", "singapore", "india", "australia", "japan", "canada",
          "toronto", "vancouver", "brazil", "mexico", "london", "paris",
          "berlin", "dublin", "amsterdam", "madrid", "tokyo", "sydney",
          "bengaluru", "hyderabad", "emea", "apac", "latam"]


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def is_data_role(title):
    t = (title or "").lower()
    keywords = ["data", "analyst", "analytics", "business intelligence",
                "bi ", "scientist", "machine learning", "ml ",
                "reporting", "data engineer"]
    return any(k in t for k in keywords)


def is_us_relevant(location):
    loc = (location or "").lower()
    if "remote" in loc:
        return True  # remote-US / remote-worldwide from a US company
    return not any(n in loc for n in NON_US)


def html_to_text(raw):
    text = html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_board(token, label):
    """List jobs, keep data roles, fetch details for those only."""
    listing = json.loads(http_get(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=false"))
    jobs = listing.get("jobs", [])
    results = []
    for j in jobs:
        title = j.get("title") or ""
        if not is_data_role(title):
            continue
        loc = (j.get("location") or {}).get("name") or ""
        if not is_us_relevant(loc):
            continue
        job_id = j.get("id")
        try:
            detail = json.loads(http_get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}"
                f"/jobs/{job_id}?questions=false"))
        except Exception as e:
            print(f"  detail failed {token}/{job_id}: {e}")
            continue
        results.append({
            "source": f"greenhouse-{token}",
            "external_id": str(job_id),
            "title": title,
            "company": detail.get("company_name") or label,
            "location": (detail.get("location") or {}).get("name") or loc,
            "job_type": None,
            "category": ", ".join(
                d.get("name", "") for d in detail.get("departments", [])) or None,
            "salary": None,
            "description": html_to_text(detail.get("content")),
            "url": detail.get("absolute_url") or j.get("absolute_url"),
            "posted_at": detail.get("first_published") or j.get("updated_at"),
        })
        time.sleep(1)  # polite rate limit
    return results


def fetch_us_boards():
    """Zero-arg entry point for scraper.py's fetcher list."""
    all_jobs = []
    for token, label in BOARDS:
        try:
            jobs = fetch_board(token, label)
            print(f"greenhouse/{token}: {len(jobs)} US data-role postings")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"greenhouse/{token} failed: {e}")
        time.sleep(2)
    return all_jobs


if __name__ == "__main__":
    jobs = fetch_us_boards()
    print(f"total: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  [{j['company']}] {j['title']} ({j['location']})")
