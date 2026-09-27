# Job Market Scraper + Ghost Job Tracker + Power BI Dashboard

An automated pipeline that collects data-job postings, scores each one against
my job-search criteria, detects **ghost jobs** (postings that sit unfilled for
months or get repeatedly reposted), and builds a styled **Power BI (.pbix)
dashboard** — fully programmatically, no Power BI Desktop required. The
dashboard refreshes daily with newly scraped postings.

Built as a portfolio project while job hunting for entry-level data roles.

## What it does

```
Greenhouse boards (10 US tech companies: Datadog, MongoDB, Stripe, …)
        │  src/scraper.py — collect postings, filter data roles, store in SQLite
        │  src/us_boards.py — Greenhouse public API, US-only locations
        │  src/ghost.py   — daily snapshots, first/last-seen tracking, ghost score
        ▼
   data/jobs.db  (SQLite)  +  snapshots table (one row per job per day)
        │  src/analyze.py — extract skill keywords, compute fit + ghost score
        ▼
   data/jobs_export.csv
        │  src/build_pbix.py — generate a themed .pbix (pbix-mcp, pure Python)
        ▼
   output/job-market-dashboard.pbix   ← download & open in Power BI Desktop
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

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/scraper.py      # collect → data/jobs.db
python src/ghost.py        # snapshots + ghost score → data/jobs.db
python src/analyze.py      # score   → data/jobs_export.csv
python src/build_pbix.py   # build   → output/job-market-dashboard.pbix
```

Or everything at once: `bash run_daily.sh`

## Tech

Python · SQLite · Power BI (.pbix generated with
[pbix-mcp](https://github.com/d0nk3yhm/pbix-mcp)) · DAX measures validated
against the model's own engine
