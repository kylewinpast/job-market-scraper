"""Real Jobs Alert: detect genuinely-new, non-ghost postings each day.

A "real new job" = first seen in today's snapshot AND posted within the
last 14 days (when a post date is known) AND ghost_score < 30 AND US
location. Reposts and long-listed ghost suspects are excluded — that
exclusion is the product's whole value proposition. The posted-date guard
keeps the digest honest when new boards are added or tracking restarts
(everything looks "first seen today" on day one).

Runs after ghost.py (needs first_seen tracked). Stdlib only.
"""
import html
import json
import os
import sqlite3
from datetime import datetime, timezone

from analyze import NON_US
from clean import normalize_location
from ghost import compute_metrics

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT, "data", "jobs.db")
DATA_DIR = os.path.join(PROJECT, "data")
OUT_DIR = os.path.join(PROJECT, "output")

GHOST_CUTOFF = 30          # below this a posting is "not a ghost"
MAX_LISTED = 40            # cap jobs shown in the digest (JSON keeps all)
MAX_POSTED_AGE_DAYS = 14   # ignore postings first seen today but posted earlier
SITE_URL = "https://kylewinpast.github.io/job-market-scraper"

NAVY = "#143D5E"
TEAL = "#1B7F79"
AMBER = "#E8A838"
RUST = "#D95D39"


def is_us(location):
    loc = (location or "").lower()
    if not loc:
        return False
    return not any(n in loc for n in NON_US)


def posted_days_ago(posted_at, today):
    """Days between today and posted_at; None when unknown/unparseable."""
    if not posted_at:
        return None
    try:
        d = datetime.strptime(str(posted_at)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (today - d).days


def find_real_new_jobs(conn, today):
    """Return list of dicts for postings first seen today, fresh and US."""
    metrics = compute_metrics(conn)
    today_d = datetime.strptime(today, "%Y-%m-%d").date()
    rows = conn.execute(
        "SELECT id, title, company, location, url, first_seen, posted_at"
        " FROM jobs WHERE substr(first_seen, 1, 10) = ?",
        (today,),
    ).fetchall()
    out = []
    for jid, title, company, location, url, first_seen, posted_at in rows:
        g = metrics.get(jid, {})
        if g.get("ghost_score", 0) >= GHOST_CUTOFF:
            continue
        if not is_us(location):
            continue
        age = posted_days_ago(posted_at, today_d)
        if age is not None and age > MAX_POSTED_AGE_DAYS:
            continue  # newly tracked, but posted long ago — not "new"
        out.append({
            "company": (company or "").strip(),
            "title": (title or "").strip(),
            "location": location or "",
            "location_clean": normalize_location(location),
            "url": url or "",
            "first_seen": str(first_seen or "")[:10],
            "posted_at": posted_at or "",
            "ghost_score": g.get("ghost_score", 0),
        })
    # Newest postings first; undated go last.
    out.sort(key=lambda r: r["posted_at"] or "", reverse=True)
    return out


def build_text(jobs, today):
    lines = [f"Ghost Job Tracker — Real Jobs Digest ({today})",
             f"{len(jobs)} genuinely-new jobs today. Zero ghosts.",
             ""]
    if not jobs:
        lines.append("No new real jobs today — the boards were quiet.")
        return "\n".join(lines) + "\n"
    shown = jobs[:MAX_LISTED]
    by_company = {}
    for j in shown:
        by_company.setdefault(j["company"] or "Unknown", []).append(j)
    for company in sorted(by_company):
        lines.append(f"== {company} ==")
        for j in by_company[company]:
            lines.append(f"  - {j['title']} ({j['location_clean']})")
            if j["url"]:
                lines.append(f"    Apply: {j['url']}")
        lines.append("")
    if len(jobs) > MAX_LISTED:
        lines.append(f"... and {len(jobs) - MAX_LISTED} more in the full list.")
    return "\n".join(lines) + "\n"


def build_html(jobs, today):
    n = len(jobs)
    shown = jobs[:MAX_LISTED]
    by_company = {}
    for j in shown:
        by_company.setdefault(j["company"] or "Unknown", []).append(j)

    if not jobs:
        body = ('<p class="empty">No new real jobs today &mdash; the boards were '
                "quiet. Check back tomorrow.</p>")
    else:
        parts = []
        for company in sorted(by_company):
            items = []
            for j in by_company[company]:
                apply = (f' <a class="apply" href="{html.escape(j["url"])}" '
                         'target="_blank" rel="noopener">Apply &rarr;</a>'
                         if j["url"] else "")
                items.append(
                    f'<li><strong>{html.escape(j["title"])}</strong>'
                    f'<span class="loc">{html.escape(j["location_clean"])}</span>'
                    f"{apply}</li>")
            parts.append(
                f'<h3>{html.escape(company)}</h3><ul>{"".join(items)}</ul>')
        if n > MAX_LISTED:
            parts.append(
                f'<p class="more">&hellip; and {n - MAX_LISTED:,} more in the '
                "full list.</p>")
        body = "\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Real Jobs Digest — {today}</title>
<style>
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         background:#F2F4F7; color:#1F2A37; line-height:1.5; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:0 16px 48px; }}
  header {{ background:{NAVY}; color:#fff; padding:32px 16px 24px; }}
  header h1 {{ margin:0 0 6px; font-size:1.6rem; }}
  header h1 .z {{ color:{AMBER}; }}
  header p {{ margin:0; color:#D7E3EC; }}
  .card {{ background:#fff; border-radius:10px; padding:20px;
           box-shadow:0 2px 8px rgba(20,61,94,.12); margin:20px 0; }}
  h3 {{ color:{NAVY}; margin:18px 0 6px; font-size:1.05rem; }}
  ul {{ margin:0 0 6px; padding-left:20px; }}
  li {{ margin:6px 0; }}
  .loc {{ color:#5A6C7D; font-size:.88rem; margin-left:8px; }}
  .apply {{ color:{TEAL}; font-weight:600; text-decoration:none; margin-left:8px;
            font-size:.88rem; white-space:nowrap; }}
  .apply:hover {{ text-decoration:underline; }}
  .empty {{ color:#5A6C7D; font-style:italic; }}
  .more {{ color:#5A6C7D; font-size:.9rem; }}
  .note {{ font-size:.85rem; color:#5A6C7D; }}
  footer {{ text-align:center; color:#5A6C7D; font-size:.82rem; padding:8px 16px 32px; }}
  footer a {{ color:{TEAL}; }}
</style>
</head>
<body>
<header><div class="wrap" style="padding-bottom:0">
  <h1>Real Jobs Digest <span class="z">&mdash; zero ghosts</span></h1>
  <p>{n:,} genuinely-new posting{"s" if n != 1 else ""} first seen on {today},
  all with a ghost score under {GHOST_CUTOFF}.</p>
</div></header>
<div class="wrap">
  <div class="card">
    {body}
  </div>
  <p class="note">A posting counts as "real" when it appears in today's board
  snapshot for the first time, was posted within the last
  {MAX_POSTED_AGE_DAYS} days, carries a ghost score under {GHOST_CUTOFF}
  (not long-listed, not a repost), and is US-based.</p>
  <footer>
    <a href="{SITE_URL}">Ghost Job Tracker</a> &middot;
    <a href="{SITE_URL}/digest/">digest archive</a>
  </footer>
</div>
</body>
</html>
"""


def main():
    today = datetime.now(timezone.utc).date().isoformat()
    conn = sqlite3.connect(DB_PATH)
    jobs = find_real_new_jobs(conn, today)
    conn.close()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    json_path = os.path.join(DATA_DIR, f"alerts_{today}.json")
    html_path = os.path.join(OUT_DIR, f"digest_{today}.html")
    text_path = os.path.join(OUT_DIR, f"digest_{today}.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "count": len(jobs), "jobs": jobs},
                  f, ensure_ascii=False, indent=1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(jobs, today))
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(build_text(jobs, today))

    print(f"alerts: {len(jobs)} real new jobs for {today}")
    print(f"alerts: wrote {json_path}, {html_path}, {text_path}")


if __name__ == "__main__":
    main()
