# Job Market Scraper + Power BI Dashboard

An automated pipeline that collects data-job postings, scores each one against
my job-search criteria, and builds a styled **Power BI (.pbix) dashboard** —
fully programmatically, no Power BI Desktop required. The dashboard refreshes
daily with newly scraped postings.

Built as a portfolio project while job hunting for entry-level data roles.

## What it does

```
Remotive API + Arbeitnow API + Greenhouse boards (10 US tech companies)
        │  src/scraper.py — collect postings, filter data roles, store in SQLite
        │  src/us_boards.py — Greenhouse API: Datadog, MongoDB, Stripe, etc.
        ▼
   data/jobs.db  (SQLite)
        │  src/analyze.py — extract skill keywords, compute fit score
        ▼
   data/jobs_export.csv
        │  src/build_pbix.py — generate a themed .pbix (pbix-mcp, pure Python)
        ▼
   output/job-market-dashboard.pbix   ← download & open in Power BI Desktop
```

## The dashboard

- **KPI cards** — total postings, average fit score, top matches (score ≥ 10)
- **Postings by location** — bar chart, sorted descending
- **Skill mentions** — bar chart of extracted keywords (SQL, Python, Tableau…)
- **Location slicer** — click to cross-filter the whole page
- **Postings table** — ranked by fit score (title, company, location, score)

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
python src/analyze.py      # score   → data/jobs_export.csv
python src/build_pbix.py   # build   → output/job-market-dashboard.pbix
```

Or everything at once: `bash run_daily.sh`

## Tech

Python · SQLite · Power BI (.pbix generated with
[pbix-mcp](https://github.com/d0nk3yhm/pbix-mcp)) · DAX measures validated
against the model's own engine
