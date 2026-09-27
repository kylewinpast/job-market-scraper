# Job Market Scraper + Ghost Job Tracker + Power BI Dashboard

An automated pipeline that collects data-job postings, scores each one against
my job-search criteria, detects **ghost jobs** (postings that sit unfilled for
months or get repeatedly reposted), and builds a styled **Power BI (.pbix)
dashboard** — fully programmatically, no Power BI Desktop required. The
dashboard refreshes daily with newly scraped postings.

Built as a portfolio project while job hunting for entry-level data roles.

## Website

Live: **https://kylewinpast.github.io/job-market-scraper/**

A public, mobile-friendly Ghost Job Tracker site (single static page, rebuilt
daily by `src/build_site.py`): KPI cards (postings tracked, suspected ghosts,
average days listed, companies), a searchable/sortable ghost watchlist with
click-to-apply links, a per-company ghost chart, and the scoring methodology.

Methodology in 3 lines: every day we snapshot which postings are still listed;
postings earn ghost points for staying up 30/60/90+ days (+20/+35/+50) or being
reposted under a new listing ID (2x → +25, 3x+ → +40, capped at 100); a score of
50+ marks a suspected ghost. Heuristic only — not an accusation against any employer.

## What it does

```
Job boards (48 US tech companies: 25 Greenhouse + 2 Lever + 21 Ashby —
Datadog, MongoDB, Stripe, Databricks, Anthropic, Palantir, OpenAI, Linear, Notion, Ramp, …)
        │  src/scraper.py — collect postings, filter data roles, store in SQLite
        │  src/us_boards.py — Greenhouse public API, US-only locations
        │  src/lever_boards.py / src/ashby_boards.py — Lever + Ashby public APIs, US-only
        │  src/ghost.py   — daily snapshots, first/last-seen tracking, ghost score
        ▼
   data/jobs.db  (SQLite)  +  snapshots table (one row per job per day)
        │  src/analyze.py — extract skill keywords, compute fit + ghost score
        ▼
   data/jobs_export.csv
        │  src/build_pbix.py — generate a themed .pbix (pbix-mcp, pure Python)
        │  src/build_site.py — generate docs/index.html (public website)
        ▼
   output/job-market-dashboard.pbix   ← download & open in Power BI Desktop
   docs/index.html                    ← published via GitHub Pages
```

## The dashboard

- **KPI cards** — total postings, average fit score, top matches (score ≥ 10), suspected ghost jobs (ghost score ≥ 50)
- **Postings by location** — bar chart, sorted descending
- **Skill mentions** — bar chart of extracted keywords (SQL, Python, Tableau…)
- **Location slicer** — click to cross-filter the whole page
- **Postings table** — ranked by fit score (title, company, location, score)
- **Ghost watchlist** — table ranked by ghost score (title, company, location, days listed, repost count, ghost score, apply link)

## Ghost Job Tracker

A "ghost job" is a posting that stays listed for months without being filled,
or the same role reposted under new IDs — both classic signs nobody is really
hiring. Every posting gets a **ghost_score (0–100)**:

| Signal | Points |
|---|---|
| Listed ≥ 90 days | +50 |
| Listed ≥ 60 days | +35 |
| Listed ≥ 30 days | +20 |
| Same role reposted ≥ 3× (same company + normalized title, new IDs) | +40 |
| Same role reposted 2× | +25 |

Capped at 100. `days_listed` uses the older of the posting's `posted_at` date
and its first-seen snapshot, so day-one data already has signal. Repost groups
are built by normalizing titles: lowercase, strip parentheticals like
"(Summer 2027)", strip trailing " - location", remove years, collapse
whitespace. Daily snapshots (`snapshots` table: one row per job per day) let
`first_seen`/`last_seen` get more accurate the longer the pipeline runs.

Navy/teal/amber theme, card shadows, formatted headers — all authored in code.

## Fit score

Each posting is scored against my criteria:

| Signal | Effect |
|---|---|
| Junior / entry-level / intern wording | + |
| Data keywords (SQL, Python, R, Tableau, Power BI, Excel…) | +2 each |
| DFW / NYC / East Coast / Remote location | + |
| Senior / principal / lead wording | −100 (excluded) |

## Email alerts — Real Jobs Digest

Each day the pipeline detects **genuinely-new postings**: first seen in
today's snapshot, ghost score under 30 (not long-listed, not a repost), and
US-based. The digest lands in `output/digest_YYYY-MM-DD.html`/`.txt` and a
public archive is published at
[kylewinpast.github.io/job-market-scraper/digest/](https://kylewinpast.github.io/job-market-scraper/digest/).

To actually send the digest by email (3 steps, ~10 min):

1. Create a free account at [resend.com](https://resend.com).
2. Verify your sending domain (Resend dashboard → Domains), or use Resend's
   test domain for trials. Update `FROM_ADDRESS` in `src/send_digest.py` to
   match.
3. `export RESEND_API_KEY="re_..." ALERT_RECIPIENTS="you@example.com"` and run
   `python src/send_digest.py` (preview first with `--dry-run`). Sending stays
   manual — the daily pipeline only *builds* the digest, never sends it.

The signup form on the website posts to `SIGNUP_FORM_ACTION` in
`src/build_site.py` — point it at your form backend
(Resend / Buttondown / Formspree) to start collecting subscribers.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/scraper.py      # collect → data/jobs.db
python src/ghost.py        # snapshots + ghost score → data/jobs.db
python src/alerts.py       # real-new-job detector → output/digest_*.html
python src/analyze.py      # score   → data/jobs_export.csv
python src/build_pbix.py   # build   → output/job-market-dashboard.pbix
```

Or everything at once: `bash run_daily.sh`

## Tech

Python · SQLite · Power BI (.pbix generated with
[pbix-mcp](https://github.com/d0nk3yhm/pbix-mcp)) · DAX measures validated
against the model's own engine
