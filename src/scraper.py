"""Job posting scraper v1: Remotive + Arbeitnow (free, no API key).
v2: + US Greenhouse boards (see us_boards.py).
Normalizes postings into a common schema and stores them in SQLite.
"""
import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone

from us_boards import fetch_us_boards

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT, "data", "jobs.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    job_type TEXT,
    category TEXT,
    salary TEXT,
    description TEXT,
    url TEXT,
    posted_at TEXT,
    scraped_at TEXT,
    UNIQUE(source, external_id)
);
"""

HEADERS = {"User-Agent": "job-market-scraper/0.1 (personal portfolio project)"}


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_remotive():
    """Remote jobs, filter to data categories."""
    url = "https://remotive.com/api/remote-jobs?category=data&limit=200"
    payload = json.loads(http_get(url))
    jobs = []
    for j in payload.get("jobs", []):
        jobs.append({
            "source": "remotive",
            "external_id": str(j.get("id")),
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": "Remote",
            "job_type": j.get("job_type"),
            "category": j.get("category"),
            "salary": j.get("salary"),
            "description": j.get("description"),
            "url": j.get("url"),
            "posted_at": j.get("publication_date"),
        })
    return jobs


def fetch_arbeitnow():
    """Remote jobs board, free JSON API."""
    url = "https://www.arbeitnow.com/api/job-board-api"
    payload = json.loads(http_get(url))
    jobs = []
    for j in payload.get("data", []):
        raw_loc = j.get("location")
        if isinstance(raw_loc, list):
            location = ", ".join(raw_loc)
        elif isinstance(raw_loc, str):
            location = raw_loc
        else:
            location = "Remote"
        jobs.append({
            "source": "arbeitnow",
            "external_id": j.get("slug"),
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": location,
            "job_type": j.get("job_types", [None])[0] if j.get("job_types") else None,
            "category": None,
            "salary": None,
            "description": j.get("description"),
            "url": j.get("url"),
            "posted_at": j.get("created_at"),
        })
    return jobs


def is_data_role(title):
    t = (title or "").lower()
    keywords = ["data", "analyst", "analytics", "business intelligence", "bi ",
                "scientist", "machine learning", "ml ", "reporting"]
    return any(k in t for k in keywords)


def save(jobs):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for j in jobs:
        if not is_data_role(j["title"]):
            continue
        try:
            conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (source, external_id, title, company, location, job_type,
                    category, salary, description, url, posted_at, scraped_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (j["source"], j["external_id"], j["title"], j["company"],
                 j["location"], j["job_type"], j["category"], j["salary"],
                 j["description"], j["url"], j["posted_at"], now),
            )
            inserted += conn.total_changes and 1 or 0
        except sqlite3.Error as e:
            print(f"DB error: {e}")
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    return inserted, count


def main():
    all_jobs = []
    # US-only: EU/international boards (Remotive, Arbeitnow) disabled per user.
    for fetcher in (fetch_us_boards,):
        try:
            jobs = fetcher()
            print(f"{fetcher.__name__}: {len(jobs)} fetched")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"{fetcher.__name__} failed: {e}")
        time.sleep(2)  # polite rate limit
    inserted, total = save(all_jobs)
    print(f"inserted ~{inserted} data-role postings, total in DB: {total}")


if __name__ == "__main__":
    main()
