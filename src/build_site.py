"""Build the public Ghost Job Tracker website.

Reads data/jobs_export.csv and generates a single self-contained
docs/index.html (inline CSS + vanilla JS, Chart.js via CDN for one chart).
Stdlib only — no build step.
"""
import csv
import html
import json
import os
from datetime import date

from seniority import seniority_label, LEVELS as SENIORITY_LEVELS

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT, "data", "jobs_export.csv")
OUT_PATH = os.path.join(PROJECT, "docs", "index.html")
OUTPUT_DIR = os.path.join(PROJECT, "output")
DATA_DIR = os.path.join(PROJECT, "data")
DIGEST_DIR = os.path.join(PROJECT, "docs", "digest")
COMPANIES_DIR = os.path.join(PROJECT, "docs", "companies")
SITE_URL = "https://kylewinpast.github.io/job-market-scraper"

# Canonical display names: strip junk, shorten legal suffixes.
DISPLAY_NAMES = {
    "Chime Financial, Inc": "Chime",
}

# Buttondown newsletter username. Subscribers sign up through Buttondown's
# public embed endpoint (no API key needed on the site); the daily pipeline
# pulls the subscriber list back via the API in src/sync_subscribers.py.
# TODO: replace with the real Buttondown username once the account exists.
BUTTONDOWN_USERNAME = "ghostjobtracker"

# Email signup form endpoint. Posts to Buttondown's embed-subscribe endpoint,
# which handles double opt-in on Buttondown's side.
SIGNUP_FORM_ACTION = (
    f"https://buttondown.email/api/emails/embed-subscribe/{BUTTONDOWN_USERNAME}"
)

NAVY = "#143D5E"
TEAL = "#1B7F79"
AMBER = "#E8A838"
RUST = "#D95D39"


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["company"] = canonical_company(r.get("company"))
    return rows


def canonical_company(name):
    """Normalize a raw company string to its canonical display name."""
    name = (name or "").strip()
    return DISPLAY_NAMES.get(name, name)


def slugify(name):
    """URL slug: lowercase, spaces -> hyphens, keep a-z0-9- only."""
    import re
    slug = name.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "company"


def company_slugs(companies):
    """Map each company name to a unique URL slug (collision-safe)."""
    slugs, used = {}, set()
    for c in sorted(companies):
        base = slugify(c)
        slug, i = base, 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        used.add(slug)
        slugs[c] = slug
    return slugs


def score_color(score):
    if score >= 75:
        return RUST
    if score >= 50:
        return AMBER
    return TEAL


# Bar for "real jobs": same threshold as the email digest (src/alerts.py).
REAL_THRESHOLD = 30


def real_job_row(r):
    """One table row for the real-jobs tabs (ghost_score < 30)."""
    score = int(r.get("ghost_score") or 0)
    url = r.get("url") or ""
    apply = (f'<a class="apply" href="{html.escape(url)}" target="_blank" '
             f'rel="noopener">Apply &rarr;</a>' if url else "")
    return (
        "<tr>"
        f"<td>{html.escape(r.get('title') or '')}</td>"
        f"<td>{html.escape(r.get('company') or '')}</td>"
        f"<td>{html.escape(r.get('location_clean') or r.get('location') or '')}</td>"
        f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
        f'<td class="num"><span class="score-badge">{score}</span></td>'
        f"<td>{apply}</td>"
        "</tr>")


def company_commentary(company, total, ghosts, avg_days, top):
    """2-3 sentences of plain-English commentary generated from the numbers."""
    pct = round(100 * ghosts / total) if total else 0
    s1 = (f"We tracked {total:,} {company} job postings. {ghosts:,} of them "
          f"({pct}%) show ghost signals \u2014 listings that stay up for months "
          f"or get reposted under new listing IDs.")
    if avg_days >= 60:
        s2 = (f"Their postings stay listed for {avg_days:,.0f} days on average, "
              f"well above a healthy hiring cycle.")
    elif avg_days >= 30:
        s2 = (f"Their postings stay listed for {avg_days:,.0f} days on average.")
    else:
        s2 = (f"Their postings turn over relatively quickly "
              f"({avg_days:,.0f} days on average).")
    if top:
        s3 = (f"The most suspicious listing is \u201c{top['title']}\u201d "
              f"({top['location_clean']}), listed {top['days_listed']:,} days "
              f"with a ghost score of {top['ghost_score']}.")
    else:
        s3 = "No individual posting currently trips our ghost-score threshold."
    return " ".join([s1, s2, s3])


def build_company_page(company, rows, today, slugs):
    """Render one per-company SEO page; returns the HTML string."""
    total = len(rows)
    scored = [int(r.get("ghost_score") or 0) for r in rows]
    ghosts = sum(1 for s in scored if s >= 50)
    avg_days = sum(int(r.get("days_listed") or 0) for r in rows) / total if total else 0
    avg_score = sum(scored) / total if total else 0

    suspects = [r for r in rows if int(r.get("ghost_score") or 0) > 0]
    suspects.sort(key=lambda r: -int(r["ghost_score"]))
    suspects = suspects[:50]
    top = None
    if suspects:
        t = suspects[0]
        top = {"title": t.get("title") or "",
               "location_clean": t.get("location_clean") or t.get("location") or "",
               "days_listed": int(t.get("days_listed") or 0),
               "ghost_score": int(t.get("ghost_score") or 0)}

    trs = []
    for r in suspects:
        score = int(r.get("ghost_score") or 0)
        url = r.get("url") or ""
        apply = (f'<a class="apply" href="{html.escape(url)}" target="_blank" '
                 f'rel="noopener">Apply &rarr;</a>' if url else "")
        trs.append(
            "<tr>"
            f"<td>{html.escape(r.get('title') or '')}</td>"
            f"<td>{html.escape(r.get('location_clean') or r.get('location') or '')}</td>"
            f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
            f'<td class="num">{int(r.get("repost_count") or 0)}</td>'
            f'<td class="num"><span class="bar" style="width:{min(score, 100)}px;'
            f'background:{score_color(score)}"></span>'
            f'<span class="score-num">{score}</span></td>'
            f"<td>{apply}</td>"
            "</tr>")
    table = ("\n".join(trs) if trs
             else '<tr><td colspan="6" class="none">No postings with ghost '
                  "signals right now.</td></tr>")

    # Real openings: ghost_score < 30 (same bar as the email digest),
    # freshest first, cap 15.
    real = [r for r in rows if int(r.get("ghost_score") or 0) < 30]
    real.sort(key=lambda r: (int(r.get("days_listed") or 0),
                             (r.get("title") or "")))
    real = real[:15]
    real_trs = []
    for r in real:
        rurl = r.get("url") or ""
        rapply = (f'<a class="apply" href="{html.escape(rurl)}" target="_blank" '
                  f'rel="noopener">Apply &rarr;</a>' if rurl else "")
        real_trs.append(
            "<tr>"
            f"<td>{html.escape(r.get('title') or '')}</td>"
            f"<td>{html.escape(r.get('location_clean') or r.get('location') or '')}</td>"
            f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
            f"<td>{rapply}</td>"
            "</tr>")
    real_table = (
        '<div class="table-wrap"><table>\n'
        "<thead><tr><th>Job title</th><th>Location</th>"
        '<th class="num">Days listed</th><th>Apply</th></tr></thead>\n'
        "<tbody>\n" + "\n".join(real_trs) + "\n</tbody>\n</table></div>"
        if real_trs else
        '<p class="none">No verified-fresh openings right now.</p>')

    kpis = [
        ("Postings tracked", f"{total:,}", TEAL),
        ("Suspected ghost jobs", f"{ghosts:,}", RUST),
        ("Average days listed", f"{avg_days:,.0f}", NAVY),
        ("Average ghost score", f"{avg_score:,.0f}", AMBER),
    ]
    kpi_html = "\n".join(
        f'''<div class="kpi"><div class="kpi-value" style="color:{color}">{html.escape(val)}</div>
        <div class="kpi-label">{html.escape(label)}</div></div>'''
        for label, val, color in kpis)

    esc_c = html.escape(company)
    meta = (f"We tracked {total:,} {company} job postings: {ghosts:,} look like "
            f"ghost jobs (listed {avg_days:,.0f} days on average). "
            f"See the full watchlist.")
    pct = round(100 * ghosts / total) if total else 0

    # Ghost rate per experience level; only levels with >= 3 postings shown.
    lvl_bits = []
    for lvl in ("entry", "mid", "senior", "exec"):
        sub = [r for r in rows if (r.get("seniority") or "mid") == lvl]
        if len(sub) >= 3:
            g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
            lvl_bits.append(f"{seniority_label(lvl)} {100.0 * g / len(sub):.0f}%")
        else:
            lvl_bits.append(f"{seniority_label(lvl)} \u2014")
    level_line = "Ghost rate by level: " + " \u00b7 ".join(lvl_bits)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ghost Jobs at {esc_c} &mdash; Ghost Job Tracker</title>
<meta name="description" content="{html.escape(meta)}">
<style>
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         background:#F2F4F7; color:#1F2A37; line-height:1.5; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 16px 48px; }}
  header {{ background:{NAVY}; color:#fff; padding:32px 16px 24px; }}
  header .wrap {{ padding-bottom:0; }}
  header h1 {{ margin:0 0 6px; font-size:1.8rem; }}
  header h1 .q {{ color:{AMBER}; }}
  header p {{ margin:0; color:#D7E3EC; }}
  .crumb {{ margin:0 0 10px; font-size:.9rem; }}
  .crumb a {{ color:{AMBER}; text-decoration:none; }}
  .crumb a:hover {{ text-decoration:underline; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:20px 0; }}
  .kpi {{ background:#fff; border-radius:10px; padding:16px; text-align:center;
         box-shadow:0 2px 8px rgba(20,61,94,.12); }}
  .kpi-value {{ font-size:1.9rem; font-weight:700; }}
  .kpi-label {{ color:#5A6C7D; font-size:.85rem; margin-top:4px; }}
  .levels {{ text-align:center; color:#5A6C7D; font-size:.9rem; margin:-6px 0 20px; }}
  section.card {{ background:#fff; border-radius:10px; padding:20px;
                 box-shadow:0 2px 8px rgba(20,61,94,.12); margin-bottom:24px; }}
  section.card h2 {{ margin:0 0 8px; color:{NAVY}; font-size:1.25rem; }}
  section.card p {{ margin:0 0 8px; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; min-width:760px; }}
  th {{ text-align:left; padding:10px 8px; color:{NAVY}; border-bottom:2px solid {NAVY};
       white-space:nowrap; }}
  td {{ padding:9px 8px; border-bottom:1px solid #E6EBF0; vertical-align:middle; }}
  tr:hover td {{ background:#F7FAFB; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  td.none {{ color:#5A6C7D; font-style:italic; text-align:center; }}
  .bar {{ display:inline-block; height:10px; border-radius:5px; vertical-align:middle; margin-right:8px; }}
  .score-num {{ font-weight:700; font-variant-numeric:tabular-nums; }}
  .apply {{ color:{TEAL}; font-weight:600; text-decoration:none; white-space:nowrap; }}
  .apply:hover {{ text-decoration:underline; }}
  .disclaimer {{ margin-top:12px; font-size:.82rem; color:#5A6C7D; font-style:italic; }}
  p.none {{ color:#5A6C7D; font-style:italic; }}
  .real-note {{ color:#5A6C7D; font-size:.9rem; margin:0 0 12px; }}
  footer {{ color:#5A6C7D; font-size:.85rem; text-align:center; padding:8px 16px 32px; }}
  footer a {{ color:{TEAL}; }}
  @media (max-width:640px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<header><div class="wrap">
  <p class="crumb"><a href="../../">&larr; All companies</a></p>
  <h1>Ghost jobs at {esc_c}<span class="q">?</span></h1>
  <p>{ghosts:,} of {total:,} tracked postings ({pct}%) show ghost signals.
     Last updated: {today}.</p>
</div></header>
<div class="wrap">
  <div class="kpis">
    {kpi_html}
  </div>
  <p class="levels">{html.escape(level_line)}</p>
  <section class="card">
    <h2>What the data says</h2>
    <p>{html.escape(company_commentary(company, total, ghosts, avg_days, top))}</p>
    <p class="disclaimer">Heuristics based on public posting data, not an accusation
    against any employer &mdash; some roles are simply evergreen or hard to fill.</p>
  </section>
  <section class="card">
    <h2>Real openings right now</h2>
    <p class="real-note">Postings with a ghost score under 30 &mdash; no 90-day
    stale listings, no reposts. Freshest first.</p>
    {real_table}
  </section>
  <section class="card">
    <h2>Top suspects at {esc_c}</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Job title</th><th>Location</th><th class="num">Days listed</th>
      <th class="num">Reposts</th><th class="num">Ghost score</th><th>Apply</th></tr></thead>
      <tbody>
        {table}
      </tbody>
    </table></div>
  </section>
  <section class="card">
    <h2>How the ghost score works</h2>
    <p>Every day we snapshot {esc_c}&rsquo;s job board and record which postings are
    still listed. A posting earns ghost points for staying up 30/60/90+ days (+20/+35/+50)
    and for being reposted under a new listing ID (+25 for 2&times;, +40 for 3&times;+),
    capped at 100. Read the <a href="../../#how-it-works"
    style="color:{TEAL};font-weight:600;">full methodology</a>.</p>
  </section>
  <footer>
    <a href="../../">Ghost Job Tracker</a> &middot;
    <a href="https://github.com/kylewinpast/job-market-scraper">GitHub</a>
  </footer>
</div>
</body>
</html>
"""


def build_company_pages(rows):
    """Write docs/companies/{slug}/index.html for every company in the CSV.

    Returns a list of dicts: company, slug, total, ghosts (score >= 50).
    """
    today = date.today().isoformat()
    by_company = {}
    for r in rows:
        c = r.get("company") or "Unknown"
        by_company.setdefault(c, []).append(r)
    slugs = company_slugs(by_company)
    pages = []
    for company in sorted(by_company):
        slug = slugs[company]
        outdir = os.path.join(COMPANIES_DIR, slug)
        os.makedirs(outdir, exist_ok=True)
        page = build_company_page(company, by_company[company], today, slugs)
        with open(os.path.join(outdir, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(page)
        ghosts = sum(1 for r in by_company[company]
                     if int(r.get("ghost_score") or 0) >= 50)
        pages.append({"company": company, "slug": slug,
                      "total": len(by_company[company]), "ghosts": ghosts})
    print(f"company pages: {len(pages)} -> {COMPANIES_DIR}/")
    return pages


def build_sitemap(pages):
    """Write docs/sitemap.xml covering main, digest, and company pages."""
    today = date.today().isoformat()
    import glob
    urls = ["", "digest/"]
    for src in sorted(glob.glob(os.path.join(
            os.path.dirname(COMPANIES_DIR), "digest", "[0-9]*.html"))):
        day = os.path.basename(src)[:-len(".html")]
        urls.append(f"digest/{day}.html")
    for p in pages:
        urls.append(f"companies/{p['slug']}/")
    items = "\n".join(
        f"  <url><loc>{SITE_URL}/{u}</loc><lastmod>{today}</lastmod></url>"
        for u in urls)
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{items}\n</urlset>\n")
    path = os.path.join(os.path.dirname(COMPANIES_DIR), "sitemap.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"sitemap: {len(urls)} urls -> {path}")
    return len(urls)


def build_robots():
    """Write docs/robots.txt allowing all + pointing at the sitemap."""
    path = os.path.join(os.path.dirname(COMPANIES_DIR), "robots.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\n"
                f"Sitemap: {SITE_URL}/sitemap.xml\n")
    print(f"robots.txt -> {path}")


def build(rows):
    total = len(rows)
    ghosts = [r for r in rows if int(r.get("ghost_score") or 0) >= 50]
    companies = {r["company"] for r in rows if r.get("company")}
    avg_days = (sum(int(r.get("days_listed") or 0) for r in rows) / total) if total else 0

    watch = [r for r in rows if int(r.get("ghost_score") or 0) > 0]
    watch.sort(key=lambda r: -int(r["ghost_score"]))
    watch = watch[:150]

    data = [{
        "title": r["title"] or "",
        "company": r["company"] or "",
        "location": r.get("location_clean") or r.get("location") or "",
        "level": seniority_label(r.get("seniority") or "mid"),
        "days": int(r.get("days_listed") or 0),
        "reposts": int(r.get("repost_count") or 0),
        "score": int(r.get("ghost_score") or 0),
        "signals": r.get("ghost_signals") or "",
        "url": r.get("url") or "",
    } for r in watch]
    # Keep </script> from ever appearing inside the embedded JSON.
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    # Per-company suspected-ghost counts for the chart.
    by_company = {}
    for r in ghosts:
        c = r.get("company") or "Unknown"
        by_company[c] = by_company.get(c, 0) + 1
    ranked = sorted(by_company.items(), key=lambda kv: -kv[1])[:10]
    chart_labels = json.dumps([c for c, _ in ranked])
    chart_values = json.dumps([n for _, n in ranked])

    # Per-company totals for the "browse by company" grid (ghosts desc).
    totals = {}
    for r in rows:
        c = r.get("company") or "Unknown"
        totals[c] = totals.get(c, 0) + 1
    slugs = company_slugs(totals)
    grid_rows = sorted(
        ({"company": c, "slug": slugs[c], "total": n,
          "ghosts": by_company.get(c, 0)} for c, n in totals.items()),
        key=lambda g: (-g["ghosts"], -g["total"]))
    grid_html = "\n".join(
        f'<div class="cocard"><a href="companies/{g["slug"]}/">'
        f'{html.escape(g["company"])}</a>'
        f'<div class="cstats">{g["total"]:,} postings &middot; '
        f'{g["ghosts"]:,} suspected ghosts</div></div>'
        for g in grid_rows)

    today = date.today().isoformat()

    # Ghost rate by experience level (Entry -> Mid -> Senior -> Executive).
    lvl_stats = []
    for lvl in SENIORITY_LEVELS:
        sub = [r for r in rows if (r.get("seniority") or "mid") == lvl]
        g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
        lvl_stats.append({
            "label": seniority_label(lvl),
            "total": len(sub), "ghosts": g,
            "rate": (100.0 * g / len(sub)) if sub else 0.0,
        })
    max_rate = max((s["rate"] for s in lvl_stats), default=0) or 1
    lvl_rows = "\n".join(
        f'<div class="lvl"><div class="lvl-name">{html.escape(s["label"])}</div>'
        f'<div class="lvl-track"><div class="lvl-fill" style="width:'
        f'{100.0 * s["rate"] / max_rate:.1f}%;background:{score_color(s["rate"])}">'
        f"</div></div>"
        f'<div class="lvl-num">{s["ghosts"]:,} of {s["total"]:,} &middot; '
        f'{s["rate"]:.0f}% ghosts</div></div>'
        for s in lvl_stats)

    # Real jobs by experience level: ghost_score < REAL_THRESHOLD,
    # freshest first, cap 100 rows per tab (totals counted in full).
    real_tabs = []
    for lvl in SENIORITY_LEVELS:
        sub = [r for r in rows
               if int(r.get("ghost_score") or 0) < REAL_THRESHOLD
               and (r.get("seniority") or "mid") == lvl]
        sub.sort(key=lambda r: (int(r.get("days_listed") or 0),
                                (r.get("title") or "")))
        real_tabs.append({"lvl": lvl, "label": seniority_label(lvl),
                          "rows": sub[:100], "total": len(sub)})

    tab_btns = "\n      ".join(
        f'<button class="tab-btn{" active" if t["lvl"] == "mid" else ""}" '
        f'data-lvl="{t["lvl"]}" role="tab" '
        f'aria-selected="{"true" if t["lvl"] == "mid" else "false"}">'
        f'{html.escape(t["label"])} ({t["total"]:,})</button>'
        for t in real_tabs)

    def tab_panel(t):
        if t["rows"]:
            body = "\n".join(real_job_row(r) for r in t["rows"])
            note = (f'<p class="tab-note">Showing the freshest 100 of '
                    f'{t["total"]:,} {html.escape(t["label"].lower())} openings.</p>'
                    if t["total"] > 100 else "")
            inner = (f'<div class="table-wrap"><table>\n'
                     "<thead><tr><th>Job title</th><th>Company</th><th>Location</th>"
                     '<th class="num">Days listed</th><th class="num">Ghost score</th>'
                     "<th>Apply</th></tr></thead>\n<tbody>\n" + body +
                     "\n</tbody>\n</table></div>" + note)
        else:
            inner = ('<p class="none">No verified-fresh openings at this level '
                     "right now.</p>")
        active = " active" if t["lvl"] == "mid" else ""
        return (f'<div class="tab-panel{active}" id="tab-{t["lvl"]}" '
                f'role="tabpanel">\n{inner}\n</div>')

    tab_panels = "\n".join(tab_panel(t) for t in real_tabs)

    kpis = [
        ("Postings tracked", f"{total:,}", TEAL),
        ("Suspected ghost jobs", f"{len(ghosts):,}", RUST),
        ("Average days listed", f"{avg_days:,.0f}", NAVY),
        ("Companies tracked", f"{len(companies):,}", AMBER),
    ]
    kpi_html = "\n".join(
        f'''<div class="kpi"><div class="kpi-value" style="color:{color}">{html.escape(val)}</div>
        <div class="kpi-label">{html.escape(label)}</div></div>'''
        for label, val, color in kpis
    )

    n_companies = len(companies)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ghost Job Tracker</title>
<meta name="description" content="We track how long job postings stay listed — and flag the ghosts.">
<style>
  :root {{ --navy:{NAVY}; --teal:{TEAL}; --amber:{AMBER}; --rust:{RUST};
           --bg:#F2F4F7; --card:#fff; --ink:#1F2A37; --muted:#5A6C7D; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         background:var(--bg); color:var(--ink); line-height:1.5; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 16px 48px; }}
  header.hero {{ background:var(--navy); color:#fff; padding:40px 16px 32px; }}
  header.hero .wrap {{ padding-bottom:0; }}
  header.hero h1 {{ margin:0 0 8px; font-size:2rem; }}
  header.hero h1 .ghost {{ color:var(--amber); }}
  header.hero p.tagline {{ margin:0 0 6px; color:#D7E3EC; font-size:1.05rem; }}
  header.hero p.updated {{ margin:0 0 14px; color:#9FB3C3; font-size:.85rem; }}
  .signup {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18);
            border-radius:10px; padding:14px 16px; max-width:560px; }}
  .signup h2 {{ margin:0 0 4px; font-size:1.05rem; color:#fff; }}
  .signup p {{ margin:0 0 10px; color:#D7E3EC; font-size:.9rem; }}
  .signup form {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .signup input[type=email] {{ flex:1; min-width:200px; padding:10px 12px; font-size:.95rem;
      border:none; border-radius:8px; }}
  .signup button {{ padding:10px 18px; font-size:.95rem; font-weight:700; color:{NAVY};
      background:{AMBER}; border:none; border-radius:8px; cursor:pointer; }}
  .signup button:hover {{ filter:brightness(1.08); }}
  .signup .fineprint {{ margin:8px 0 0; color:#A9C0D1; font-size:.8rem; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:-24px 0 24px; }}
  .kpi {{ background:var(--card); border-radius:10px; padding:16px; text-align:center;
         box-shadow:0 2px 8px rgba(20,61,94,.12); }}
  .kpi-value {{ font-size:1.9rem; font-weight:700; }}
  .kpi-label {{ color:var(--muted); font-size:.85rem; margin-top:4px; }}
  section.card {{ background:var(--card); border-radius:10px; padding:20px;
                 box-shadow:0 2px 8px rgba(20,61,94,.12); margin-bottom:24px; }}
  section.card h2 {{ margin:0 0 4px; color:var(--navy); font-size:1.3rem; }}
  section.card p.sub {{ margin:0 0 12px; color:var(--muted); font-size:.9rem; }}
  .controls {{ display:flex; gap:12px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }}
  .controls input[type=search] {{ flex:1; min-width:200px; padding:9px 12px; font-size:.95rem;
      border:1px solid #C9D4DD; border-radius:8px; }}
  .count {{ color:var(--muted); font-size:.85rem; white-space:nowrap; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem; min-width:760px; }}
  th {{ text-align:left; padding:10px 8px; color:var(--navy); border-bottom:2px solid var(--navy);
       cursor:pointer; user-select:none; white-space:nowrap; }}
  th:hover {{ color:var(--teal); }}
  td {{ padding:9px 8px; border-bottom:1px solid #E6EBF0; vertical-align:middle; }}
  tr:hover td {{ background:#F7FAFB; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  th.num {{ text-align:right; }}
  .bar {{ display:inline-block; height:10px; border-radius:5px; vertical-align:middle; margin-right:8px; }}
  .score-num {{ font-weight:700; font-variant-numeric:tabular-nums; }}
  .apply {{ color:var(--teal); font-weight:600; text-decoration:none; white-space:nowrap; }}
  .apply:hover {{ text-decoration:underline; }}
  .method {{ width:100%; border-collapse:collapse; font-size:.9rem; min-width:0; }}
  .method th {{ cursor:default; }}
  .method td, .method th {{ padding:8px; }}
  .disclaimer {{ margin-top:12px; font-size:.82rem; color:var(--muted); font-style:italic; }}
  #companyChart {{ max-height:320px; }}
  .lvl {{ display:grid; grid-template-columns:130px 1fr 170px; gap:10px;
         align-items:center; margin:10px 0; font-size:.92rem; }}
  .lvl-name {{ font-weight:700; color:var(--navy); }}
  .lvl-track {{ background:#E6EBF0; border-radius:6px; height:12px; }}
  .lvl-fill {{ height:12px; border-radius:6px; min-width:4px; }}
  .lvl-num {{ text-align:right; color:var(--muted); font-variant-numeric:tabular-nums;
             white-space:nowrap; }}
  .controls select {{ padding:9px 12px; font-size:.95rem; border:1px solid #C9D4DD;
      border-radius:8px; background:#fff; }}
  .tabs {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
  .tab-btn {{ padding:9px 16px; font-size:.92rem; font-weight:600; color:var(--navy);
      background:#E6EBF0; border:none; border-radius:20px; cursor:pointer; }}
  .tab-btn:hover {{ background:#D5DFE8; }}
  .tab-btn.active {{ background:var(--teal); color:#fff; }}
  .tab-panel {{ display:none; }}
  .tab-panel.active {{ display:block; }}
  .score-badge {{ display:inline-block; min-width:34px; padding:2px 8px; border-radius:12px;
      background:var(--teal); color:#fff; font-weight:700; font-size:.8rem; text-align:center; }}
  .tab-note {{ color:var(--muted); font-size:.85rem; margin:8px 0 0; }}
  p.none {{ color:var(--muted); font-style:italic; }}
  .cogrid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:10px; }}
  .cocard {{ background:var(--bg); border-radius:8px; padding:12px 14px; }}
  .cocard a {{ color:var(--navy); font-weight:700; text-decoration:none; }}
  .cocard a:hover {{ color:var(--teal); text-decoration:underline; }}
  .cocard .cstats {{ color:var(--muted); font-size:.82rem; margin-top:2px; }}
  footer {{ color:var(--muted); font-size:.85rem; text-align:center; padding:8px 16px 32px; }}
  footer a {{ color:var(--teal); }}
  @media (max-width:640px) {{
    .kpis {{ grid-template-columns:repeat(2,1fr); margin-top:16px; }}
    header.hero h1 {{ font-size:1.5rem; }}
  }}
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <h1>Ghost Job <span class="ghost">Tracker</span></h1>
    <p class="tagline">We track how long job postings stay listed &mdash; and flag the ghosts.</p>
    <p class="updated">Last updated: {today} &middot; {total:,} postings tracked daily</p>
    <div class="signup">
      <h2>Get the real jobs, skip the ghosts</h2>
      <p>A free digest of genuinely-new postings &mdash; no ghost jobs, no spam.</p>
      <form action="{SIGNUP_FORM_ACTION}" method="post">
        <input type="email" name="email" placeholder="you@example.com" required
               aria-label="Email address">
        <button type="submit">Notify me</button>
      </form>
      <p class="fineprint">Free forever. Unsubscribe anytime.</p>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="kpis">
    {kpi_html}
  </div>

  <section class="card">
    <h2>Real jobs by experience level</h2>
    <p class="sub">Postings with a ghost score under 30 &mdash; no 90-day stale listings, no reposts.
    Freshest first.</p>
    <div class="tabs" role="tablist">
      {tab_btns}
    </div>
    {tab_panels}
  </section>

  <section class="card">
    <h2>Suspected ghosts by company</h2>
    <p class="sub">Postings with a ghost score of 50 or more, per company.</p>
    <canvas id="companyChart"></canvas>
  </section>

  <section class="card">
    <h2>Ghost rate by experience level</h2>
    <p class="sub">Share of postings with a ghost score of 50+, per seniority band.
    Entry-level postings are the least likely to be ghosts &mdash; internships are real hiring.</p>
    <div class="lvls">
      {lvl_rows}
    </div>
  </section>

  <section class="card">
    <h2>Browse by company</h2>
    <p class="sub">Ghost-job stats for every company we track &mdash; most suspected ghosts first.</p>
    <div class="cogrid">
      {grid_html}
    </div>
  </section>

  <section class="card">
    <h2>Ghost watchlist</h2>
    <p class="sub">Every posting showing ghost signals, ranked by ghost score. Click a column to sort.</p>
    <div class="controls">
      <input type="search" id="q" placeholder="Search title or company&hellip;" aria-label="Search">
      <select id="level" aria-label="Filter by experience level">
        <option value="">All levels</option>
        <option>Entry-level</option>
        <option>Mid-level</option>
        <option>Senior</option>
        <option>Executive</option>
      </select>
      <span class="count" id="count"></span>
    </div>
    <div class="table-wrap">
      <table id="watch">
        <thead><tr>
          <th data-k="title">Job title</th>
          <th data-k="company">Company</th>
          <th data-k="level">Level</th>
          <th data-k="location">Location</th>
          <th data-k="days" class="num">Days listed</th>
          <th data-k="reposts" class="num">Reposts</th>
          <th data-k="score" class="num">Ghost score</th>
          <th>Apply</th>
        </tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </section>

  <section class="card" id="how-it-works">
    <h2>How it works</h2>
    <p class="sub">Every day we snapshot the job boards of {n_companies} US tech companies and record which
    postings are still listed. A posting earns ghost points when it stays up for a long time
    or keeps getting reposted under a new listing ID:</p>
    <table class="method">
      <thead><tr><th>Signal</th><th class="num">Points</th></tr></thead>
      <tbody>
        <tr><td>Listed 30+ days</td><td class="num">+20</td></tr>
        <tr><td>Listed 60+ days</td><td class="num">+35</td></tr>
        <tr><td>Listed 90+ days</td><td class="num">+50</td></tr>
        <tr><td>Reposted 2&times; (same role, new listing)</td><td class="num">+25</td></tr>
        <tr><td>Reposted 3&times; or more</td><td class="num">+40</td></tr>
        <tr><td><strong>Maximum score</strong></td><td class="num"><strong>100</strong></td></tr>
      </tbody>
    </table>
    <p class="disclaimer">These are heuristics based on public posting data, not an accusation
    against any employer &mdash; some roles are simply evergreen or hard to fill.</p>
  </section>

  <section class="card">
    <h2>Daily digest</h2>
    <p class="sub">Genuinely-new postings, zero ghosts. Browse the
    <a href="digest/" style="color:{TEAL};font-weight:600;">digest archive</a>.</p>
  </section>

  <footer>
    Data: daily snapshots of {n_companies} US tech company boards
    (Greenhouse / Lever / Ashby).<br>
    Built as a portfolio project by Geonung Weon &middot;
    <a href="https://github.com/kylewinpast/job-market-scraper">github.com/kylewinpast/job-market-scraper</a>
  </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
var DATA = {data_json};
var LABELS = {chart_labels};
var VALUES = {chart_values};

function esc(s) {{
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {{
    return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c];
  }});
}}
function scoreColor(s) {{
  if (s >= 75) return "{RUST}";
  if (s >= 50) return "{AMBER}";
  return "{TEAL}";
}}

var sortKey = "score", sortDir = -1, query = "", levelFilter = "";
var tbody = document.getElementById("rows");
var countEl = document.getElementById("count");

function filtered() {{
  var q = query.trim().toLowerCase();
  var rows = DATA.filter(function (r) {{
    if (levelFilter && r.level !== levelFilter) return false;
    return !q || r.title.toLowerCase().indexOf(q) !== -1 ||
           r.company.toLowerCase().indexOf(q) !== -1;
  }});
  rows.sort(function (a, b) {{
    var x = a[sortKey], y = b[sortKey];
    if (typeof x === "number") return (x - y) * sortDir;
    return String(x).localeCompare(String(y)) * sortDir;
  }});
  return rows;
}}

function render() {{
  var rows = filtered();
  var h = "";
  for (var i = 0; i < rows.length; i++) {{
    var r = rows[i];
    h += "<tr>" +
      "<td>" + esc(r.title) + "</td>" +
      "<td>" + esc(r.company) + "</td>" +
      "<td>" + esc(r.level) + "</td>" +
      "<td>" + esc(r.location) + "</td>" +
      "<td class=\\"num\\">" + r.days.toLocaleString() + "</td>" +
      "<td class=\\"num\\">" + r.reposts + "</td>" +
      "<td class=\\"num\\"><span class=\\"bar\\" style=\\"width:" + Math.min(r.score,100) +
        "px;background:" + scoreColor(r.score) + "\\"></span>" +
        "<span class=\\"score-num\\">" + r.score + "</span></td>" +
      "<td>" + (r.url ? "<a class=\\"apply\\" href=\\"" + esc(r.url) +
        "\\" target=\\"_blank\\" rel=\\"noopener\\">Apply &rarr;</a>" : "") + "</td>" +
      "</tr>";
  }}
  tbody.innerHTML = h;
  countEl.textContent = "Showing " + rows.length.toLocaleString() + " of " +
    DATA.length.toLocaleString();
}}

var ths = document.querySelectorAll("#watch th[data-k]");
function arrows() {{
  for (var i = 0; i < ths.length; i++) {{
    var k = ths[i].getAttribute("data-k");
    var base = ths[i].textContent.replace(/ [\\u25B2\\u25BC]/g, "");
    ths[i].textContent = base + (k === sortKey ? (sortDir === 1 ? " \\u25B2" : " \\u25BC") : "");
  }}
}}
for (var i = 0; i < ths.length; i++) {{
  (function (th) {{
    th.addEventListener("click", function () {{
      var k = th.getAttribute("data-k");
      if (sortKey === k) sortDir = -sortDir;
      else {{ sortKey = k; sortDir = (k === "title" || k === "company" || k === "location" || k === "level") ? 1 : -1; }}
      arrows(); render();
    }});
  }})(ths[i]);
}}
document.getElementById("q").addEventListener("input", function (e) {{
  query = e.target.value; render();
}});
document.getElementById("level").addEventListener("change", function (e) {{
  levelFilter = e.target.value; render();
}});

var tabBtns = document.querySelectorAll(".tab-btn");
function showTab(lvl) {{
  for (var i = 0; i < tabBtns.length; i++) {{
    var b = tabBtns[i];
    var on = b.getAttribute("data-lvl") === lvl;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
    var panel = document.getElementById("tab-" + b.getAttribute("data-lvl"));
    if (panel) panel.classList.toggle("active", on);
  }}
}}
for (var i = 0; i < tabBtns.length; i++) {{
  (function (b) {{
    b.addEventListener("click", function () {{
      showTab(b.getAttribute("data-lvl"));
    }});
  }})(tabBtns[i]);
}}
arrows(); render();

if (window.Chart && LABELS.length) {{
  new Chart(document.getElementById("companyChart"), {{
    type: "bar",
    data: {{ labels: LABELS,
      datasets: [{{ data: VALUES, backgroundColor: "{TEAL}", borderRadius: 4 }}] }},
    options: {{ indexAxis: "y",
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ x: {{ beginAtZero: true, ticks: {{ precision: 0 }} }} }} }}
  }});
}} else {{
  document.getElementById("companyChart").style.display = "none";
}}
</script>
</body>
</html>
"""

def build_digest_archive():
    """Copy each day's digest into docs/digest/ and build the archive index."""
    import glob
    import shutil
    os.makedirs(DIGEST_DIR, exist_ok=True)
    entries = []
    for src in sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html"))):
        base = os.path.basename(src)              # digest_YYYY-MM-DD.html
        day = base[len("digest_"):-len(".html")]
        dst = os.path.join(DIGEST_DIR, f"{day}.html")
        shutil.copyfile(src, dst)
        count = None
        meta = os.path.join(DATA_DIR, f"alerts_{day}.json")
        if os.path.exists(meta):
            try:
                with open(meta, encoding="utf-8") as f:
                    count = json.load(f).get("count")
            except (OSError, ValueError):
                pass
        entries.append((day, count))
    entries.sort(reverse=True)

    items = []
    for day, count in entries:
        label = (f"{count:,} real new jobs" if count is not None
                 else "digest")
        items.append(
            f'<li><a href="{html.escape(day)}.html">{html.escape(day)}</a>'
            f' <span class="n">{html.escape(label)}</span></li>')
    body = "\n".join(items) if items else "<p>No digests yet.</p>"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Digest archive — Ghost Job Tracker</title>
<style>
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         background:#F2F4F7; color:#1F2A37; line-height:1.5; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:0 16px 48px; }}
  header {{ background:{NAVY}; color:#fff; padding:32px 16px 24px; }}
  header h1 {{ margin:0; font-size:1.6rem; }}
  header h1 .z {{ color:{AMBER}; }}
  header p {{ margin:6px 0 0; color:#D7E3EC; }}
  header a {{ color:{AMBER}; }}
  ul {{ list-style:none; margin:20px 0; padding:0; }}
  li {{ background:#fff; border-radius:10px; padding:14px 18px; margin:10px 0;
       box-shadow:0 2px 8px rgba(20,61,94,.12); }}
  li a {{ color:{TEAL}; font-weight:700; text-decoration:none; font-size:1.05rem; }}
  li a:hover {{ text-decoration:underline; }}
  .n {{ color:#5A6C7D; font-size:.9rem; margin-left:10px; }}
</style>
</head>
<body>
<header><div class="wrap" style="padding-bottom:0">
  <h1>Digest <span class="z">archive</span></h1>
  <p>Every daily Real Jobs Digest. <a href="../">&larr; back to Ghost Job Tracker</a></p>
</div></header>
<div class="wrap">
  <ul>
    {body}
  </ul>
</div>
</body>
</html>
"""
    with open(os.path.join(DIGEST_DIR, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(page)
    print(f"digest archive: {len(entries)} digest(s) -> {DIGEST_DIR}/index.html")
    return len(entries)


def main():
    rows = load_rows()
    page = build(rows)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {OUT_PATH} ({len(page):,} bytes, {len(rows)} postings)")
    build_digest_archive()
    pages = build_company_pages(rows)
    build_sitemap(pages)
    build_robots()


if __name__ == "__main__":
    main()
