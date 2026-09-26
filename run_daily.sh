#!/bin/bash
# Daily job-market pipeline: scrape -> analyze -> build .pbix
set -e
cd "$HOME/workspace/projects/job-market-scraper"
.venv/bin/python src/scraper.py
.venv/bin/python src/analyze.py
.venv/bin/python src/build_pbix.py
ls -la output/job-market-dashboard.pbix
