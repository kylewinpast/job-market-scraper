"""Analyze collected postings: skill keywords + fit score, export CSV for Power BI."""
import csv
import os
import re
import sqlite3

from clean import normalize_location
from ghost import compute_metrics

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT, "data", "jobs.db")
OUT_PATH = os.path.join(PROJECT, "data", "jobs_export.csv")

SKILLS = ["sql", "python", "r ", "tableau", "power bi", "powerbi", "excel",
          "vba", "sap", "snowflake", "databricks", "aws", "azure", "gcp",
          "spark", "etl", "dashboard", "a/b", "statistics", "regression"]

SENIOR_TERMS = ["senior", "sr.", "principal", "staff", "lead", "director",
                "vp ", "vice president", "manager", "head of"]
JUNIOR_TERMS = ["junior", "jr.", "entry", "entry-level", "associate", " i ",
                "analyst i", "i -"]

DFW = ["dallas", "plano", "mckinney", "frisco", "irving", "fort worth",
       "arlington", "richardson", "addison", "allen"]
EAST = ["new york", "nyc", "manhattan", "brooklyn", "new jersey", "nj",
        "boston", "philadelphia", "washington", "d.c.", "atlanta", "charlotte"]
# Non-US postings (from EU boards) rank lower for a US job search.
NON_US = ["france", "germany", "united kingdom", " ireland", "spain",
          "netherlands", "belgium", "sweden", "poland", "portugal",
          "italy", "singapore", "india", "australia", "japan", "canada",
          "toronto", "vancouver", "brazil", "mexico", "london", "paris",
          "berlin", "dublin", "amsterdam", "madrid", "tokyo", "sydney",
          "bengaluru", "hyderabad", "emea", "apac", "latam", "deutschland"]


def contains_skill(text, skill):
    """Word-boundary match so 'r' doesn't match 'for ' etc."""
    return re.search(r"\b" + re.escape(skill.strip()) + r"\b", text) is not None


def fit_score(title, description, location):
    t = f" {(title or '')} ".lower()
    d = (description or "").lower()
    loc = (location or "").lower()
    score, reasons = 0, []

    if any(s in t for s in SENIOR_TERMS):
        return -100, ["senior-level (excluded)"]
    for j in JUNIOR_TERMS:
        if j.strip() and j in t:
            score += 20
            reasons.append("entry-level title")
            break
    for s in SKILLS:
        if contains_skill(d, s) or contains_skill(t, s):
            score += 2
    if "remote" in loc:
        score += 10
        reasons.append("remote")
    if any(c in loc for c in DFW):
        score += 10
        reasons.append("DFW")
    if any(c in loc for c in EAST):
        score += 10
        reasons.append("East Coast")
    if "remote" not in loc and any(n in loc for n in NON_US):
        score -= 10
        reasons.append("non-US location")
    return score, reasons


def extract_skills(title, description):
    text = f"{title or ''} {description or ''}".lower()
    found = [s.strip() for s in SKILLS if contains_skill(text, s)]
    return "|".join(found)


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, source, title, company, location, job_type, salary, url, posted_at, description FROM jobs"
    ).fetchall()
    ghost_metrics = compute_metrics(conn)
    conn.close()

    out = []
    for jid, source, title, company, location, job_type, salary, url, posted_at, desc in rows:
        score, reasons = fit_score(title, desc, location)
        g = ghost_metrics.get(jid, {})
        out.append({
            "source": source, "title": title, "company": company,
            "location": location, "location_clean": normalize_location(location),
            "job_type": job_type, "salary": salary,
            "url": url, "posted_at": posted_at,
            "skills": extract_skills(title, desc),
            "fit_score": score, "fit_reasons": "|".join(reasons),
            "days_listed": g.get("days_listed", 0),
            "repost_count": g.get("repost_count", 0),
            "ghost_score": g.get("ghost_score", 0),
            "ghost_signals": g.get("ghost_signals", ""),
        })
    out.sort(key=lambda r: r["fit_score"], reverse=True)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    top = [r for r in out if r["fit_score"] > 0][:5]
    print(f"exported {len(out)} rows → {OUT_PATH}")
    print("top matches:")
    for r in top:
        print(f"  [{r['fit_score']}] {r['title']} @ {r['company']} ({r['location']})")


if __name__ == "__main__":
    main()
