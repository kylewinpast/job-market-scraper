"""Ghost Job Tracker: detect postings that stay listed for months or get
repeatedly reposted without real hiring.

Pipeline: jobs.db -> first_seen/last_seen tracking + daily snapshots ->
per-posting ghost_score (0-100) consumed by analyze.py (CSV) and build_pbix.py.

Stdlib only: sqlite3, re, datetime.
"""
import os
import re
import sqlite3
from datetime import date, datetime, timezone

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT, "data", "jobs.db")


def ensure_schema(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
    if "first_seen" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN first_seen TEXT")
    if "last_seen" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN last_seen TEXT")
    conn.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_date TEXT,
        source TEXT,
        external_id TEXT,
        PRIMARY KEY(snapshot_date, source, external_id)
    )""")
    conn.commit()


def backfill(conn):
    """Seed first_seen/last_seen for jobs scraped before tracking existed."""
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("""
        UPDATE jobs
        SET first_seen = COALESCE(first_seen, scraped_at, posted_at, ?),
            last_seen  = COALESCE(last_seen, scraped_at, ?)
        WHERE first_seen IS NULL
    """, (now, now))
    conn.commit()
    return cur.rowcount


def record_snapshot(conn):
    """Record today's (source, external_id) pairs; refresh first/last seen."""
    today = datetime.now(timezone.utc).date().isoformat()
    rows = conn.execute("SELECT source, external_id FROM jobs").fetchall()
    conn.executemany(
        "INSERT OR IGNORE INTO snapshots (snapshot_date, source, external_id)"
        " VALUES (?, ?, ?)",
        [(today, s, e) for s, e in rows])
    conn.execute("""
        UPDATE jobs SET
            first_seen = (SELECT MIN(snapshot_date) FROM snapshots
                          WHERE snapshots.source = jobs.source
                            AND snapshots.external_id = jobs.external_id),
            last_seen  = (SELECT MAX(snapshot_date) FROM snapshots
                          WHERE snapshots.source = jobs.source
                            AND snapshots.external_id = jobs.external_id)
    """)
    conn.commit()
    return today, len(rows)


def normalize_title(title):
    """Normalize a job title so reposts of the same role group together."""
    t = (title or "").lower()
    t = re.sub(r"\([^)]*\)", " ", t)          # "(summer 2027)", "(hybrid)", ...
    t = re.sub(r"\s*[-–—]\s*[a-z][a-z ,.'&]*$", " ", t)  # trailing " - new york"
    t = re.sub(r"\b20\d{2}\b", " ", t)         # years: 2026, 2027, ...
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _days_ago(today, s):
    if not s:
        return 0
    s = str(s).strip()
    if "T" in s:                              # ISO datetime -> date part
        s = s.split("T", 1)[0]
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    return max((today - d).days, 0)


def compute_metrics(conn):
    """Return {job_id: {days_listed, repost_count, ghost_score, ghost_signals}}."""
    today = date.today()
    rows = conn.execute(
        "SELECT id, source, external_id, title, company,"
        " first_seen, last_seen, posted_at FROM jobs"
    ).fetchall()

    # Group postings that are the same role reposted: same company +
    # normalized title -> set of distinct (source, external_id).
    groups = {}
    keys = {}
    for jid, source, ext_id, title, company, *_rest in rows:
        key = ((company or "").strip().lower(), normalize_title(title))
        keys[jid] = key
        groups.setdefault(key, set()).add((source, ext_id))

    out = {}
    for jid, _s, _e, _t, _c, first_seen, _last, posted_at in rows:
        days_listed = max(_days_ago(today, first_seen),
                          _days_ago(today, posted_at))
        repost_count = len(groups[keys[jid]])
        score, signals = 0, []
        if days_listed >= 90:
            score += 50
            signals.append(f"listed {days_listed} days")
        elif days_listed >= 60:
            score += 35
            signals.append(f"listed {days_listed} days")
        elif days_listed >= 30:
            score += 20
            signals.append(f"listed {days_listed} days")
        if repost_count >= 3:
            score += 40
            signals.append(f"reposted {repost_count}x")
        elif repost_count == 2:
            score += 25
            signals.append(f"reposted {repost_count}x")
        out[jid] = {
            "days_listed": days_listed,
            "repost_count": repost_count,
            "ghost_score": min(score, 100),
            "ghost_signals": "|".join(signals),
        }
    return out


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    n_back = backfill(conn)
    today, n_snap = record_snapshot(conn)
    metrics = compute_metrics(conn)
    conn.close()
    suspects = sum(1 for m in metrics.values() if m["ghost_score"] >= 50)
    print(f"ghost: backfilled {n_back} rows, tracking {len(metrics)} jobs")
    print(f"ghost: recorded {n_snap} snapshots for {today}")
    print(f"ghost: {suspects} suspected ghost jobs (score >= 50)")


if __name__ == "__main__":
    main()
