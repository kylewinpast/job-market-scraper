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

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT, "data", "jobs_export.csv")
OUT_PATH = os.path.join(PROJECT, "docs", "index.html")
OUTPUT_DIR = os.path.join(PROJECT, "output")
DATA_DIR = os.path.join(PROJECT, "data")
DIGEST_DIR = os.path.join(PROJECT, "docs", "digest")

# Email signup form endpoint. Default "#" does nothing — replace with a real
# form backend endpoint (Resend, Buttondown, Formspree, ...) to collect
# subscribers, e.g. "https://api.buttondown.email/v1/subscribers".
SIGNUP_FORM_ACTION = "#"

NAVY = "#143D5E"
TEAL = "#1B7F79"
AMBER = "#E8A838"
RUST = "#D95D39"


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score_color(score):
    if score >= 75:
        return RUST
    if score >= 50:
        return AMBER
    return TEAL


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

    today = date.today().isoformat()
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
      <!-- Replace the form action with your email backend endpoint
           (Resend, Buttondown, Formspree, ...). See SIGNUP_FORM_ACTION in src/build_site.py. -->
      <form action="{SIGNUP_FORM_ACTION}" method="post">
        <input type="email" name="email" placeholder="you@example.com" required
               aria-label="Email address">
        <button type="submit">Notify me</button>
      </form>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="kpis">
    {kpi_html}
  </div>

  <section class="card">
    <h2>Suspected ghosts by company</h2>
    <p class="sub">Postings with a ghost score of 50 or more, per company.</p>
    <canvas id="companyChart"></canvas>
  </section>

  <section class="card">
    <h2>Ghost watchlist</h2>
    <p class="sub">Every posting showing ghost signals, ranked by ghost score. Click a column to sort.</p>
    <div class="controls">
      <input type="search" id="q" placeholder="Search title or company&hellip;" aria-label="Search">
      <span class="count" id="count"></span>
    </div>
    <div class="table-wrap">
      <table id="watch">
        <thead><tr>
          <th data-k="title">Job title</th>
          <th data-k="company">Company</th>
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

  <section class="card">
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

var sortKey = "score", sortDir = -1, query = "";
var tbody = document.getElementById("rows");
var countEl = document.getElementById("count");

function filtered() {{
  var q = query.trim().toLowerCase();
  var rows = DATA.filter(function (r) {{
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
      else {{ sortKey = k; sortDir = (k === "title" || k === "company" || k === "location") ? 1 : -1; }}
      arrows(); render();
    }});
  }})(ths[i]);
}}
document.getElementById("q").addEventListener("input", function (e) {{
  query = e.target.value; render();
}});
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


if __name__ == "__main__":
    main()
