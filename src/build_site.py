"""Build the public Ghost Job Tracker website.

Reads data/jobs_export.csv and generates docs/ (GitHub Pages):
  index.html            main page
  companies/{slug}/    per-company SEO pages (46)
  roles/{slug}/        per-role SEO pages (7)
  cities/{slug}/       per-city SEO pages (10)
  report/              shareable Ghost Jobs Report
  digest/              daily digest archive
Design: "Ghostlight" — editorial data-journalism system. Fraunces (display
serif) + Inter (body), hairline borders, tabular numerals, restrained
red/green semantic color. Static HTML/CSS/vanilla JS only. Stdlib only.
"""
import csv
import html
import json
import os
from datetime import date

from seniority import seniority_label, LEVELS as SENIORITY_LEVELS
from role import classify as classify_role, role_label

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT, "data", "jobs_export.csv")
OUT_PATH = os.path.join(PROJECT, "docs", "index.html")
OUTPUT_DIR = os.path.join(PROJECT, "output")
DATA_DIR = os.path.join(PROJECT, "data")
DIGEST_DIR = os.path.join(PROJECT, "docs", "digest")
COMPANIES_DIR = os.path.join(PROJECT, "docs", "companies")
ROLES_DIR = os.path.join(PROJECT, "docs", "roles")
CITIES_DIR = os.path.join(PROJECT, "docs", "cities")
REPORT_DIR = os.path.join(PROJECT, "docs", "report")
SITE_URL = "https://kylewinpast.github.io/job-market-scraper"

# Canonical display names: strip junk, shorten legal suffixes.
DISPLAY_NAMES = {
    "Chime Financial, Inc": "Chime",
}

# Buttondown newsletter username. Subscribers sign up through Buttondown's
# public embed endpoint (no API key needed on the site); the daily pipeline
# pulls the subscriber list back via the API in src/sync_subscribers.py.
BUTTONDOWN_USERNAME = "ghostjpbtracker"

# Email signup form endpoint. Posts to Buttondown's embed-subscribe endpoint,
# which handles double opt-in on Buttondown's side.
SIGNUP_FORM_ACTION = (
    f"https://buttondown.email/api/emails/embed-subscribe/{BUTTONDOWN_USERNAME}"
)

# ---------------------------------------------------------------------------
# Design system: "Ghostlight"
# Editorial data-journalism look. Fraunces (display serif) + Inter (body).
# Mostly monochrome; red = ghost signals, green = real jobs, deep blue =
# links/CTAs. Hairline borders, no heavy shadows, tabular numerals.
# ---------------------------------------------------------------------------
INK = "#0E1116"        # near-black text / dark surfaces
INK_SOFT = "#1B2129"
MUTED = "#5D6B7A"      # secondary text
FAINT = "#8A94A1"      # tertiary text
LINE = "#E7E9EC"       # hairline borders
PAPER = "#FFFFFF"
PAPER_DIM = "#F6F7F8"  # alt section background
GHOST = "#D92D20"      # ghost-signal red
GHOST_DEEP = "#B42318"
REAL = "#12805C"       # real-job green
ACCENT = "#175CD3"     # links / primary CTAs

FONTS_URL = ("https://fonts.googleapis.com/css2?"
             "family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&"
             "family=Inter:wght@400;500;600;700;800&display=swap")

# Simple ghost mark: white ghost on a dark rounded square.
FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
    "<rect width='64' height='64' rx='14' fill='%230B0E13'/>"
    "<path d='M32 12c-10 0-16 8-16 18v18l5-4 5 4 6-4 6 4 5-4 5 4V30"
    "c0-10-6-18-16-18z' fill='white'/>"
    "<circle cx='25' cy='30' r='3' fill='%230B0E13'/>"
    "<circle cx='39' cy='30' r='3' fill='%230B0E13'/></svg>"
)
FAVICON_URI = "data:image/svg+xml," + FAVICON_SVG.replace("#", "%23")

BASE_CSS = """
:root {
  --ink:#0E1116; --ink-soft:#1B2129; --muted:#5D6B7A; --faint:#8A94A1;
  --line:#E7E9EC; --paper:#FFFFFF; --paper-dim:#F6F7F8;
  --ghost:#D92D20; --ghost-deep:#B42318; --real:#12805C; --accent:#175CD3;
  --serif:"Fraunces",Georgia,"Times New Roman",serif;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body {
  margin:0; font-family:var(--sans); background:var(--paper); color:var(--ink);
  line-height:1.6; font-size:16px; -webkit-font-smoothing:antialiased;
}
::selection { background:#FBD9D5; }
.wrap { max-width:1120px; margin:0 auto; padding:0 24px; }
.wrap-narrow { max-width:820px; margin:0 auto; padding:0 24px; }
.num, .tnum { font-variant-numeric:tabular-nums; font-feature-settings:"tnum"; }

/* ---------- sticky nav ---------- */
.nav {
  position:sticky; top:0; z-index:50;
  background:rgba(255,255,255,.88); backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px); border-bottom:1px solid var(--line);
}
.nav-inner {
  max-width:1120px; margin:0 auto; padding:0 24px; height:60px;
  display:flex; align-items:center; gap:28px;
}
.brand { display:flex; align-items:center; gap:10px; text-decoration:none; color:var(--ink); }
.brand img { width:26px; height:26px; display:block; }
.brand b { font-weight:800; font-size:1rem; letter-spacing:-0.01em; }
.brand b span { color:var(--ghost); }
.nav-links { display:flex; gap:22px; margin-left:8px; }
.nav-links a {
  color:var(--muted); text-decoration:none; font-size:.9rem; font-weight:500;
}
.nav-links a:hover { color:var(--ink); }
.nav-cta { margin-left:auto; }
.btn {
  display:inline-block; padding:10px 20px; border-radius:8px;
  background:var(--accent); color:#fff; font-weight:600; font-size:.92rem;
  text-decoration:none; border:none; cursor:pointer; line-height:1.4;
}
.btn:hover { background:#0F4FBB; }
.btn-ghost-red { background:var(--ghost); }
.btn-ghost-red:hover { background:var(--ghost-deep); }
.btn-outline {
  background:transparent; color:var(--ink); border:1px solid var(--line);
}
.btn-outline:hover { border-color:var(--faint); background:var(--paper-dim); }

/* ---------- hero ---------- */
.hero { background:#0B0E13; color:#fff; overflow:hidden; position:relative; }
.hero::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(900px 420px at 18% -10%, rgba(217,45,32,.16), transparent 60%);
}
.hero-inner {
  max-width:1120px; margin:0 auto; padding:88px 24px 72px; position:relative; z-index:1;
}
.eyebrow {
  display:inline-flex; align-items:center; gap:8px;
  font-size:.75rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:#F2B8B2; margin:0 0 20px;
}
.eyebrow .dot { width:7px; height:7px; border-radius:50%; background:var(--ghost); }
.hero h1 {
  font-family:var(--serif); font-weight:600; letter-spacing:-0.015em;
  font-size:clamp(2.6rem, 6vw, 4.4rem); line-height:1.05; margin:0 0 20px; max-width:16em;
}
.hero h1 .stat { color:#FF6B5E; }
.hero .lede {
  font-size:clamp(1.02rem, 1.6vw, 1.2rem); color:#C6CFD9; max-width:38em; margin:0 0 32px;
}
.hero-ctas { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin-bottom:40px; }
.hero .btn { padding:13px 26px; font-size:1rem; border-radius:10px; }
.hero-note { color:#8A94A1; font-size:.85rem; }
.hero-note a { color:#C6CFD9; }
.signup-inline { display:flex; gap:0; max-width:480px; }
.signup-inline input[type=email] {
  flex:1; min-width:0; padding:13px 16px; font-size:1rem; font-family:var(--sans);
  border:1px solid rgba(255,255,255,.2); border-right:none; border-radius:10px 0 0 10px;
  background:rgba(255,255,255,.07); color:#fff;
}
.signup-inline input[type=email]::placeholder { color:#8A94A1; }
.signup-inline input[type=email]:focus { outline:2px solid var(--accent); outline-offset:-2px; }
.signup-inline button {
  padding:13px 24px; font-size:1rem; font-weight:700; font-family:var(--sans);
  background:var(--ghost); color:#fff; border:none; border-radius:0 10px 10px 0; cursor:pointer;
  white-space:nowrap;
}
.signup-inline button:hover { background:var(--ghost-deep); }
.kpi-strip {
  display:grid; grid-template-columns:repeat(4,1fr);
  border-top:1px solid rgba(255,255,255,.14); margin-top:8px; padding-top:28px;
}
.kpi-dark { padding:4px 28px 4px 0; }
.kpi-dark + .kpi-dark { border-left:1px solid rgba(255,255,255,.14); padding-left:28px; }
.kpi-dark .v {
  font-size:clamp(1.9rem, 3vw, 2.6rem); font-weight:800; letter-spacing:-0.02em;
  font-variant-numeric:tabular-nums;
}
.kpi-dark .v.red { color:#FF6B5E; }
.kpi-dark .v.green { color:#5ED3A3; }
.kpi-dark .l { color:#9AA5B2; font-size:.85rem; margin-top:4px; }

/* ---------- sections ---------- */
.section { padding:72px 0; }
.section.alt { background:var(--paper-dim); border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.sec-head { max-width:720px; margin-bottom:36px; }
.sec-eyebrow {
  font-size:.75rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
  color:var(--ghost); margin:0 0 10px;
}
.sec-eyebrow.green { color:var(--real); }
.sec-eyebrow.blue { color:var(--accent); }
.sec-head h2 {
  font-family:var(--serif); font-weight:600; letter-spacing:-0.01em;
  font-size:clamp(1.7rem, 3vw, 2.3rem); line-height:1.15; margin:0 0 10px;
}
.sec-head p { color:var(--muted); margin:0; font-size:1.02rem; }

/* ---------- stat cards ---------- */
.kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.kpi {
  background:var(--paper); border:1px solid var(--line); border-radius:12px;
  padding:22px 20px;
}
.kpi .v { font-size:2rem; font-weight:800; letter-spacing:-0.02em; font-variant-numeric:tabular-nums; }
.kpi .l { color:var(--muted); font-size:.87rem; margin-top:6px; }

/* ---------- bars ---------- */
.barrow { display:grid; grid-template-columns:150px 1fr 190px; gap:14px; align-items:center; padding:9px 0; border-bottom:1px solid var(--line); font-size:.93rem; }
.barrow:last-child { border-bottom:none; }
.barrow .n { font-weight:600; }
.barrow .n a { color:var(--ink); text-decoration:none; }
.barrow .n a:hover { color:var(--accent); text-decoration:underline; }
.barrow .track { background:#EEF0F3; border-radius:6px; height:10px; }
.barrow .fill { height:10px; border-radius:6px; min-width:3px; }
.barrow .v { text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
.barrow .v b { color:var(--ink); }

/* ---------- tables ---------- */
.controls { display:flex; gap:12px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }
.controls input[type=search] {
  flex:1; min-width:200px; padding:10px 14px; font-size:.95rem; font-family:var(--sans);
  border:1px solid var(--line); border-radius:8px; background:var(--paper);
}
.controls input[type=search]:focus { outline:2px solid var(--accent); outline-offset:-1px; border-color:var(--accent); }
.controls select {
  padding:10px 14px; font-size:.95rem; font-family:var(--sans);
  border:1px solid var(--line); border-radius:8px; background:var(--paper);
}
.count { color:var(--faint); font-size:.85rem; white-space:nowrap; }
.table-wrap { overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--paper); }
table.data { width:100%; border-collapse:collapse; font-size:.9rem; min-width:780px; }
table.data thead th {
  text-align:left; padding:12px 14px; font-size:.72rem; font-weight:700;
  letter-spacing:.08em; text-transform:uppercase; color:var(--faint);
  border-bottom:1px solid var(--line); background:var(--paper-dim);
  white-space:nowrap; cursor:pointer; user-select:none;
}
table.data thead th:hover { color:var(--ink); }
table.data thead th.num, table.data td.num { text-align:right; }
table.data td { padding:12px 14px; border-bottom:1px solid var(--line); vertical-align:middle; }
table.data tbody tr:last-child td { border-bottom:none; }
table.data tbody tr:hover td { background:#F8FAFC; }
table.data td.num { font-variant-numeric:tabular-nums; white-space:nowrap; }
.scorebar { display:inline-flex; align-items:center; gap:8px; }
.scorebar .track { width:72px; background:#EEF0F3; border-radius:5px; height:8px; }
.scorebar .fill { height:8px; border-radius:5px; }
.scorebar .n { font-weight:700; font-variant-numeric:tabular-nums; min-width:24px; text-align:right; }
.badge-real {
  display:inline-block; padding:3px 10px; border-radius:20px; font-size:.78rem; font-weight:700;
  background:#E3F4EC; color:var(--real);
}
.apply { color:var(--accent); font-weight:600; text-decoration:none; white-space:nowrap; font-size:.9rem; }
.apply:hover { text-decoration:underline; }
td.none, p.none { color:var(--faint); font-style:italic; }
td.none { text-align:center; padding:24px; }

/* ---------- tabs (underline style) ---------- */
.tabs { display:flex; gap:4px; border-bottom:1px solid var(--line); margin-bottom:20px; overflow-x:auto; }
.tab-btn {
  padding:12px 18px; font-size:.95rem; font-weight:600; font-family:var(--sans);
  color:var(--muted); background:none; border:none; cursor:pointer; white-space:nowrap;
  border-bottom:2px solid transparent; margin-bottom:-1px;
}
.tab-btn:hover { color:var(--ink); }
.tab-btn.active { color:var(--ink); border-bottom-color:var(--ghost); }
.tab-btn .cnt { color:var(--faint); font-weight:500; font-size:.85rem; margin-left:6px; }
.tab-btn.active .cnt { color:var(--muted); }
.tab-panel { display:none; }
.tab-panel.active { display:block; }
.tab-note { color:var(--faint); font-size:.85rem; margin:12px 0 0; }

/* ---------- browse grids ---------- */
.cogrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }
.cocard {
  border:1px solid var(--line); border-radius:12px; padding:16px 18px; background:var(--paper);
  transition:border-color .15s ease;
}
.cocard:hover { border-color:#C9CFD6; }
.cocard a { color:var(--ink); font-weight:700; text-decoration:none; font-size:1rem; }
.cocard a:hover { color:var(--accent); }
.cocard .cstats { color:var(--muted); font-size:.85rem; margin-top:4px; font-variant-numeric:tabular-nums; }
.cocard .cstats b { color:var(--ghost); font-weight:700; }
.taglist { display:flex; flex-wrap:wrap; gap:10px; }
.tag {
  display:inline-flex; align-items:baseline; gap:10px; padding:9px 16px;
  border:1px solid var(--line); border-radius:24px; text-decoration:none; background:var(--paper);
}
.tag b { color:var(--ink); font-size:.9rem; font-weight:600; }
.tag span { color:var(--faint); font-size:.8rem; font-variant-numeric:tabular-nums; }
.tag:hover { border-color:#C9CFD6; background:var(--paper-dim); }

/* ---------- report promo / cta ---------- */
.promo {
  background:#0B0E13; color:#fff; border-radius:16px; padding:48px;
  display:grid; grid-template-columns:1.2fr .8fr; gap:32px; align-items:center; position:relative; overflow:hidden;
}
.promo::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(600px 300px at 85% 20%, rgba(217,45,32,.18), transparent 60%);
}
.promo h2 { font-family:var(--serif); font-weight:600; font-size:clamp(1.6rem,3vw,2.2rem); margin:0 0 10px; position:relative; z-index:1; }
.promo p { color:#C6CFD9; margin:0 0 20px; position:relative; z-index:1; }
.promo .bignum {
  font-family:var(--serif); font-size:clamp(3.4rem,7vw,5.2rem); font-weight:700; color:#FF6B5E;
  line-height:1; position:relative; z-index:1; text-align:right;
}
.promo .bignum small { display:block; font-family:var(--sans); font-size:.85rem; color:#9AA5B2; font-weight:500; margin-top:8px; }
.newsletter {
  border:1px solid var(--line); border-radius:16px; padding:44px; background:var(--paper-dim);
  text-align:center;
}
.newsletter h2 { font-family:var(--serif); font-size:clamp(1.5rem,2.6vw,2rem); font-weight:600; margin:0 0 8px; }
.newsletter p { color:var(--muted); margin:0 0 22px; }
.newsletter form { display:flex; gap:0; max-width:460px; margin:0 auto; }
.newsletter input[type=email] {
  flex:1; min-width:0; padding:13px 16px; font-size:1rem; font-family:var(--sans);
  border:1px solid var(--line); border-right:none; border-radius:10px 0 0 10px; background:#fff;
}
.newsletter input[type=email]:focus { outline:2px solid var(--accent); outline-offset:-2px; }
.newsletter button {
  padding:13px 26px; font-size:1rem; font-weight:700; font-family:var(--sans);
  background:var(--ink); color:#fff; border:none; border-radius:0 10px 10px 0; cursor:pointer; white-space:nowrap;
}
.newsletter button:hover { background:var(--ink-soft); }
.fineprint { color:var(--faint); font-size:.82rem; margin:12px 0 0; }

/* ---------- methodology table ---------- */
table.method { width:100%; border-collapse:collapse; font-size:.95rem; }
table.method th {
  text-align:left; padding:10px 12px; font-size:.72rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--faint); border-bottom:1px solid var(--line);
}
table.method td { padding:10px 12px; border-bottom:1px solid var(--line); }
table.method td.num, table.method th.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.disclaimer { margin-top:14px; font-size:.85rem; color:var(--faint); font-style:italic; }

/* ---------- topic pages (company / role / city) ---------- */
.pagehead { border-bottom:1px solid var(--line); padding:40px 0 32px; }
.crumb { font-size:.88rem; margin:0 0 14px; }
.crumb a { color:var(--accent); text-decoration:none; font-weight:500; }
.crumb a:hover { text-decoration:underline; }
.pagehead h1 {
  font-family:var(--serif); font-weight:600; letter-spacing:-0.01em;
  font-size:clamp(2rem,4.5vw,3rem); line-height:1.08; margin:0 0 12px;
}
.pagehead h1 .q { color:var(--ghost); }
.pagehead .sub { color:var(--muted); font-size:1.05rem; margin:0; max-width:44em; }
.level-line { color:var(--muted); font-size:.92rem; margin:20px 0 0; font-variant-numeric:tabular-nums; }
.prose { font-size:1.02rem; }
.prose p { margin:0 0 12px; }

/* ---------- report page ---------- */
.report-hero { background:#0B0E13; color:#fff; padding:96px 0 72px; position:relative; overflow:hidden; }
.report-hero::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(1000px 500px at 50% -10%, rgba(217,45,32,.22), transparent 65%);
}
.report-hero .bignum {
  font-family:var(--serif); font-weight:700; color:#FF6B5E;
  font-size:clamp(4.5rem,14vw,9rem); line-height:1; letter-spacing:-0.02em;
}
.report-hero h1 {
  font-family:var(--serif); font-weight:600; font-size:clamp(1.8rem,4vw,2.8rem);
  margin:16px 0 16px; letter-spacing:-0.01em; max-width:20em;
}
.report-hero .lede { color:#C6CFD9; font-size:1.1rem; max-width:40em; margin:0; }
.report-hero .dateline { color:#8A94A1; font-size:.85rem; margin:28px 0 0; }
.pullquote {
  border-left:3px solid var(--ghost); padding:8px 0 8px 24px; margin:36px 0;
}
.pullquote .big {
  font-family:var(--serif); font-size:clamp(2rem,5vw,3rem); font-weight:700; color:var(--ghost-deep);
  line-height:1.1; letter-spacing:-0.01em;
}
.pullquote .cap { color:var(--muted); margin-top:8px; font-size:.95rem; }

/* ---------- digest archive ---------- */
.dlist { list-style:none; margin:28px 0 0; padding:0; }
.dlist li {
  border:1px solid var(--line); border-radius:12px; padding:18px 22px; margin:12px 0;
  display:flex; align-items:baseline; gap:14px; background:var(--paper);
}
.dlist li a { color:var(--accent); font-weight:700; text-decoration:none; font-size:1.05rem; font-variant-numeric:tabular-nums; }
.dlist li a:hover { text-decoration:underline; }
.dlist .n { color:var(--faint); font-size:.9rem; }

/* ---------- footer ---------- */
footer.site {
  border-top:1px solid var(--line); background:var(--paper-dim); margin-top:0;
}
.foot-inner {
  max-width:1120px; margin:0 auto; padding:48px 24px 40px;
  display:grid; grid-template-columns:1.4fr 1fr 1fr; gap:32px;
}
.foot-brand p { color:var(--muted); font-size:.9rem; margin:10px 0 0; max-width:30em; }
.foot-col h3 {
  font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--faint); margin:0 0 14px;
}
.foot-col a { display:block; color:var(--muted); text-decoration:none; font-size:.92rem; margin:8px 0; }
.foot-col a:hover { color:var(--ink); }
.foot-base {
  max-width:1120px; margin:0 auto; padding:20px 24px 28px; border-top:1px solid var(--line);
  color:var(--faint); font-size:.82rem; display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap;
}
.foot-base a { color:var(--muted); }

/* ---------- responsive ---------- */
@media (max-width:860px) {
  .nav-links { display:none; }
  .kpi-strip { grid-template-columns:repeat(2,1fr); gap:20px 0; }
  .kpi-dark { padding:4px 16px 4px 0; }
  .kpi-dark:nth-child(3) { border-left:none; padding-left:0; }
  .kpis { grid-template-columns:repeat(2,1fr); }
  .promo { grid-template-columns:1fr; padding:36px 28px; }
  .promo .bignum { text-align:left; }
  .foot-inner { grid-template-columns:1fr; }
  .barrow { grid-template-columns:110px 1fr 130px; }
}
@media (max-width:560px) {
  .section { padding:52px 0; }
  .hero-inner { padding:64px 24px 52px; }
  .signup-inline, .newsletter form { flex-direction:column; }
  .signup-inline input[type=email], .newsletter input[type=email] {
    border-right:1px solid var(--line); border-radius:10px; margin-bottom:10px;
  }
  .signup-inline input[type=email] { border-color:rgba(255,255,255,.2); }
  .signup-inline button, .newsletter button { border-radius:10px; }
  .barrow { grid-template-columns:96px 1fr 108px; font-size:.85rem; }
  .newsletter { padding:32px 22px; }
}
"""


def page_head(title, description, og_url, og_type="website"):
    """Shared <head>: meta, OG/twitter tags, fonts, favicon, design CSS."""
    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{og_url}">
<meta property="og:site_name" content="Ghost Job Tracker">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(description)}">
<link rel="icon" href="{FAVICON_URI}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS_URL}" rel="stylesheet">
<style>{BASE_CSS}</style>"""


def ghost_mark_img():
    return f'<img src="{FAVICON_URI}" alt="Ghost Job Tracker" width="26" height="26">'


def site_nav(home_prefix="", cta=True):
    """Sticky nav. home_prefix: relative path back to site root ('' on main)."""
    links = "".join(
        f'<a href="{home_prefix}#{a}">{l}</a>'
        for a, l in [("ghost-rate", "Ghost rate"), ("watchlist", "Watchlist"),
                     ("real-jobs", "Real jobs"), ("companies", "Companies"),
                     ("report", "Report")])
    cta_html = (f'<span class="nav-cta"><a class="btn" href="{home_prefix}#newsletter">'
                f'Get the digest</a></span>' if cta else "")
    return f"""<nav class="nav"><div class="nav-inner">
  <a class="brand" href="{home_prefix or './'}">{ghost_mark_img()}<b>Ghost Job <span>Tracker</span></b></a>
  <div class="nav-links">{links}</div>
  {cta_html}
</div></nav>"""


def site_footer(n_companies, today, home_prefix=""):
    return f"""<footer class="site">
  <div class="foot-inner">
    <div class="foot-brand">
      <a class="brand" href="{home_prefix or './'}">{ghost_mark_img()}<b>Ghost Job <span>Tracker</span></b></a>
      <p>We snapshot the job boards of {n_companies} US tech companies every day
      and score each posting for ghost signals &mdash; stale listings and silent
      reposts &mdash; so job seekers can skip the ghosts.</p>
    </div>
    <div class="foot-col">
      <h3>Explore</h3>
      <a href="{home_prefix}#real-jobs">Real jobs by level</a>
      <a href="{home_prefix}#watchlist">Ghost watchlist</a>
      <a href="{home_prefix}report/">Ghost Jobs Report</a>
      <a href="{home_prefix}digest/">Digest archive</a>
    </div>
    <div class="foot-col">
      <h3>Project</h3>
      <a href="{home_prefix}#how-it-works">Methodology</a>
      <a href="https://github.com/kylewinpast/job-market-scraper">GitHub</a>
      <a href="{home_prefix}sitemap.xml">Sitemap</a>
    </div>
  </div>
  <div class="foot-base">
    <span>Data as of {today} &middot; updated daily from public job boards (Greenhouse / Lever / Ashby).</span>
    <span>Heuristics, not accusations &mdash; some roles are simply evergreen.</span>
  </div>
</footer>"""


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

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
        return GHOST_DEEP
    if score >= 50:
        return GHOST
    return REAL


# Bar for "real jobs": same threshold as the email digest (src/alerts.py).
REAL_THRESHOLD = 30


def apply_link(url):
    url = url or ""
    if not url:
        return ""
    return (f'<a class="apply" href="{html.escape(url)}" target="_blank" '
            f'rel="noopener">Apply &rarr;</a>')


def scorebar_html(score):
    """Refined ghost-score bar: thin track + red fill + tabular number."""
    w = min(max(int(score), 0), 100)
    return (f'<span class="scorebar"><span class="track">'
            f'<span class="fill" style="display:block;width:{w}%;'
            f'background:{score_color(score)}"></span></span>'
            f'<span class="n">{int(score)}</span></span>')


def real_job_row(r):
    """One table row for the real-jobs tabs (ghost_score < 30)."""
    score = int(r.get("ghost_score") or 0)
    return (
        "<tr>"
        f"<td>{html.escape(r.get('title') or '')}</td>"
        f"<td>{html.escape(r.get('company') or '')}</td>"
        f"<td>{html.escape(r.get('location_clean') or r.get('location') or '')}</td>"
        f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
        f'<td class="num"><span class="badge-real">score {score}</span></td>'
        f"<td>{apply_link(r.get('url'))}</td>"
        "</tr>")


def topic_stats(rows):
    """Aggregate stats for a group of postings (company, role bucket, metro)."""
    total = len(rows)
    scored = [int(r.get("ghost_score") or 0) for r in rows]
    ghosts = sum(1 for s in scored if s >= 50)
    avg_days = (sum(int(r.get("days_listed") or 0) for r in rows) / total
                if total else 0)
    avg_score = sum(scored) / total if total else 0
    suspects = sorted(
        (r for r in rows if int(r.get("ghost_score") or 0) > 0),
        key=lambda r: -int(r["ghost_score"]))[:50]
    top = None
    if suspects:
        t = suspects[0]
        top = {"title": t.get("title") or "",
               "company": t.get("company") or "",
               "location_clean": (t.get("location_clean")
                                  or t.get("location") or ""),
               "days_listed": int(t.get("days_listed") or 0),
               "ghost_score": int(t.get("ghost_score") or 0)}
    real = sorted(
        (r for r in rows if int(r.get("ghost_score") or 0) < REAL_THRESHOLD),
        key=lambda r: (int(r.get("days_listed") or 0),
                       (r.get("title") or "")))[:15]
    return {"total": total, "ghosts": ghosts, "avg_days": avg_days,
            "avg_score": avg_score, "suspects": suspects, "top": top,
            "real": real}


def level_line_for(rows):
    """'Ghost rate by level: Entry-level 9% · ...' (levels with >= 3 postings)."""
    bits = []
    for lvl in ("entry", "mid", "senior", "exec"):
        sub = [r for r in rows if (r.get("seniority") or "mid") == lvl]
        if len(sub) >= 3:
            g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
            bits.append(f"{seniority_label(lvl)} {100.0 * g / len(sub):.0f}%")
        else:
            bits.append(f"{seniority_label(lvl)} \u2014")
    return "Ghost rate by level: " + " \u00b7 ".join(bits)


def group_rows(rows, key_fn, min_n=5):
    """Group rows by key_fn, keeping only groups with >= min_n postings."""
    groups = {}
    for r in rows:
        k = key_fn(r)
        groups.setdefault(k, []).append(r)
    return {k: v for k, v in groups.items() if len(v) >= min_n}


def city_of(r):
    """Canonical metro for a posting row."""
    return (r.get("location_clean") or r.get("location") or "Unknown").strip()


# ---------------------------------------------------------------------------
# Unified topic page (company / role / city SEO pages)
# ---------------------------------------------------------------------------

def commentary_text(noun, total, ghosts, avg_days, top, company=None):
    """2-3 sentences of plain-English commentary generated from the numbers."""
    pct = round(100 * ghosts / total) if total else 0
    s1 = (f"We tracked {total:,} {noun}. {ghosts:,} of them ({pct}%) show "
          f"ghost signals \u2014 listings that stay up for months or get "
          f"reposted under new listing IDs.")
    if avg_days >= 60:
        s2 = (f"They stay listed for {avg_days:,.0f} days on average, well "
              f"above a healthy hiring cycle.")
    elif avg_days >= 30:
        s2 = f"They stay listed for {avg_days:,.0f} days on average."
    else:
        s2 = (f"They turn over relatively quickly ({avg_days:,.0f} days on "
              f"average).")
    if top:
        where = f" at {top['company']}" if company is None and top.get("company") else ""
        s3 = (f"The most suspicious listing is \u201c{top['title']}\u201d{where} "
              f"({top['location_clean']}), listed {top['days_listed']:,} days "
              f"with a ghost score of {top['ghost_score']}.")
    else:
        s3 = "No individual posting currently trips our ghost-score threshold."
    return " ".join([s1, s2, s3])


def build_topic_page(doc_title, meta_desc, h1_html, subtitle, stats, rows,
                     today, crumb_href, crumb_label, commentary,
                     second_col_header, second_col_fn, page_url_path,
                     n_companies):
    """Render a generic SEO stat page (company, role, or city).

    second_col: (header label, row -> cell text). page_url_path: canonical
    path under SITE_URL, e.g. "companies/acme/".
    """
    total, ghosts = stats["total"], stats["ghosts"]
    pct = round(100 * ghosts / total) if total else 0

    trs = []
    for r in stats["suspects"]:
        score = int(r.get("ghost_score") or 0)
        trs.append(
            "<tr>"
            f"<td>{html.escape(r.get('title') or '')}</td>"
            f"<td>{html.escape(second_col_fn(r))}</td>"
            f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
            f'<td class="num">{int(r.get("repost_count") or 0)}</td>'
            f'<td class="num">{scorebar_html(score)}</td>'
            f"<td>{apply_link(r.get('url'))}</td>"
            "</tr>")
    table = ("\n".join(trs) if trs
             else '<tr><td colspan="6" class="none">No postings with ghost '
                  "signals right now.</td></tr>")

    real_trs = []
    for r in stats["real"]:
        real_trs.append(
            "<tr>"
            f"<td>{html.escape(r.get('title') or '')}</td>"
            f"<td>{html.escape(second_col_fn(r))}</td>"
            f'<td class="num">{int(r.get("days_listed") or 0):,}</td>'
            f"<td>{apply_link(r.get('url'))}</td>"
            "</tr>")
    real_table = (
        '<div class="table-wrap"><table class="data">\n'
        f"<thead><tr><th>Job title</th><th>{html.escape(second_col_header)}</th>"
        '<th class="num">Days listed</th><th>Apply</th></tr></thead>\n'
        "<tbody>\n" + "\n".join(real_trs) + "\n</tbody>\n</table></div>"
        if real_trs else
        '<p class="none">No verified-fresh openings right now.</p>')

    kpi_defs = [
        ("Postings tracked", f"{total:,}", INK),
        ("Suspected ghost jobs", f"{ghosts:,}", GHOST),
        ("Average days listed", f"{stats['avg_days']:,.0f}", INK_SOFT),
        ("Average ghost score", f"{stats['avg_score']:,.0f}", MUTED),
    ]
    kpi_html = "\n".join(
        f'''<div class="kpi"><div class="v">{html.escape(val)}</div>
        <div class="l">{html.escape(label)}</div></div>'''
        for label, val, _ in kpi_defs)

    method_note = (
        "Every day we snapshot the job boards of US tech companies and record "
        "which postings are still listed. A posting earns ghost points for "
        "staying up 30/60/90+ days (+20/+35/+50) and for being reposted under "
        "a new listing ID (+25 for 2\u00d7, +40 for 3\u00d7+), capped at 100. "
        f'Read the <a href="{crumb_href}#how-it-works" '
        'style="color:#175CD3;font-weight:600;">full methodology</a>.')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{page_head(doc_title, meta_desc, f"{SITE_URL}/{page_url_path}")}
</head>
<body>
{site_nav(home_prefix=crumb_href)}
<div class="pagehead"><div class="wrap">
  <p class="crumb"><a href="{crumb_href}">&larr; {html.escape(crumb_label)}</a></p>
  <h1>{h1_html}</h1>
  <p class="sub">{subtitle} Last updated: {today}.</p>
  <p class="level-line">{html.escape(level_line_for(rows))}</p>
</div></div>
<div class="wrap">
  <div class="section" style="padding:40px 0 0;">
    <div class="kpis">
      {kpi_html}
    </div>
  </div>
  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">Analysis</p>
      <h2>What the data says</h2>
    </div>
    <div class="prose">
      <p>{html.escape(commentary)}</p>
      <p class="disclaimer">Heuristics based on public posting data, not an accusation
      against any employer &mdash; some roles are simply evergreen or hard to fill.</p>
    </div>
  </div>
  <div class="section alt" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow green">Verified fresh</p>
      <h2>Real openings right now</h2>
      <p>Postings with a ghost score under {REAL_THRESHOLD} &mdash; no 90-day stale
      listings, no reposts. Freshest first.</p>
    </div>
    {real_table}
  </div>
  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">Watchlist</p>
      <h2>Top suspects</h2>
    </div>
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Job title</th><th>{html.escape(second_col_header)}</th>
      <th class="num">Days listed</th><th class="num">Reposts</th>
      <th class="num">Ghost score</th><th>Apply</th></tr></thead>
      <tbody>
        {table}
      </tbody>
    </table></div>
  </div>
  <div class="section alt" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow blue">Methodology</p>
      <h2>How the ghost score works</h2>
    </div>
    <div class="prose"><p>{method_note}</p></div>
  </div>
</div>
{site_footer(n_companies, today, home_prefix=crumb_href)}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Company / role / city page builders
# ---------------------------------------------------------------------------

def build_company_pages(rows, n_companies):
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
        crows = by_company[company]
        stats = topic_stats(crows)
        total, ghosts = stats["total"], stats["ghosts"]
        pct = round(100 * ghosts / total) if total else 0
        esc_c = html.escape(company)
        doc_title = f"Ghost Jobs at {company} \u2014 Ghost Job Tracker"
        meta = (f"We tracked {total:,} {company} job postings: {ghosts:,} "
                f"({pct}%) look like ghost jobs "
                f"(listed {stats['avg_days']:,.0f} days on average). "
                f"See the full watchlist and verified-fresh openings.")
        h1 = f"Ghost jobs at {esc_c}<span class=\"q\">?</span>"
        subtitle = (f"{ghosts:,} of {total:,} tracked postings ({pct}%) show "
                    f"ghost signals.")
        commentary = commentary_text(f"{company} job postings", total, ghosts,
                                     stats["avg_days"], stats["top"],
                                     company=company)
        slug = slugs[company]
        outdir = os.path.join(COMPANIES_DIR, slug)
        os.makedirs(outdir, exist_ok=True)
        page = build_topic_page(
            doc_title, meta, h1, subtitle, stats, crows, today, "../../",
            "Ghost Job Tracker", commentary,
            "Location", lambda r: r.get("location_clean") or r.get("location") or "",
            f"companies/{slug}/", n_companies)
        with open(os.path.join(outdir, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(page)
        pages.append({"company": company, "slug": slug,
                      "total": total, "ghosts": ghosts})
    print(f"company pages: {len(pages)} -> {COMPANIES_DIR}/")
    return pages


def build_role_pages(role_groups, role_slugs, today, n_companies):
    """Write docs/roles/{slug}/index.html for each qualifying role bucket."""
    pages = []
    for role in sorted(role_groups):
        rows = role_groups[role]
        stats = topic_stats(rows)
        label = role_label(role)
        total, ghosts = stats["total"], stats["ghosts"]
        pct = round(100 * ghosts / total) if total else 0
        doc_title = f"Ghost Jobs for {label} Roles \u2014 Ghost Job Tracker"
        meta = (f"We tracked {total:,} {label.lower()} job postings: {ghosts:,} "
                f"({pct}%) look like ghost jobs "
                f"(listed {stats['avg_days']:,.0f} days on average). "
                f"See the full watchlist.")
        h1 = f"Ghost jobs in {html.escape(label)}<span class=\"q\">?</span>"
        subtitle = (f"{ghosts:,} of {total:,} tracked {label.lower()} postings "
                    f"({pct}%) show ghost signals.")
        commentary = commentary_text(f"{label} job postings", total, ghosts,
                                     stats["avg_days"], stats["top"])
        slug = role_slugs[role]
        outdir = os.path.join(ROLES_DIR, slug)
        os.makedirs(outdir, exist_ok=True)
        page = build_topic_page(
            doc_title, meta, h1, subtitle, stats, rows, today, "../../",
            "Ghost Job Tracker", commentary,
            "Company", lambda r: r.get("company") or "",
            f"roles/{slug}/", n_companies)
        with open(os.path.join(outdir, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(page)
        pages.append({"role": role, "label": label, "slug": slug,
                      "total": total, "ghosts": ghosts})
    print(f"role pages: {len(pages)} -> {ROLES_DIR}/")
    return pages


def build_city_pages(city_groups, city_slugs, today, n_companies):
    """Write docs/cities/{slug}/index.html for each qualifying metro."""
    pages = []
    for city in sorted(city_groups):
        rows = city_groups[city]
        stats = topic_stats(rows)
        total, ghosts = stats["total"], stats["ghosts"]
        pct = round(100 * ghosts / total) if total else 0
        doc_title = f"Ghost Jobs in {city} \u2014 Ghost Job Tracker"
        meta = (f"We tracked {total:,} job postings in {city}: {ghosts:,} "
                f"({pct}%) look like ghost jobs "
                f"(listed {stats['avg_days']:,.0f} days on average). "
                f"See the full watchlist.")
        h1 = f"Ghost jobs in {html.escape(city)}<span class=\"q\">?</span>"
        subtitle = (f"{ghosts:,} of {total:,} tracked postings in "
                    f"{html.escape(city)} ({pct}%) show ghost signals.")
        commentary = commentary_text(f"job postings in {city}", total, ghosts,
                                     stats["avg_days"], stats["top"])
        slug = city_slugs[city]
        outdir = os.path.join(CITIES_DIR, slug)
        os.makedirs(outdir, exist_ok=True)
        page = build_topic_page(
            doc_title, meta, h1, subtitle, stats, rows, today, "../../",
            "Ghost Job Tracker", commentary,
            "Company", lambda r: r.get("company") or "",
            f"cities/{slug}/", n_companies)
        with open(os.path.join(outdir, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(page)
        pages.append({"city": city, "slug": slug,
                      "total": total, "ghosts": ghosts})
    print(f"city pages: {len(pages)} -> {CITIES_DIR}/")
    return pages


# ---------------------------------------------------------------------------
# Ghost Jobs Report — magazine-style shareable page
# ---------------------------------------------------------------------------

def barrow_html(name, name_href, total, ghosts, rate, max_rate, color):
    """One horizontal bar row: name | bar | 'g of n · r% ghosts'.

    If total is None, the value reads 'n suspected ghosts' (main page
    top-companies strip).
    """
    n_html = (f'<a href="{name_href}">{html.escape(name)}</a>' if name_href
              else html.escape(name))
    v = (f"<b>{ghosts:,}</b> suspected ghosts" if total is None else
         f"<b>{ghosts:,}</b> of {total:,} &middot; {rate:.0f}% ghosts")
    return (
        f'<div class="barrow"><div class="n">{n_html}</div>'
        f'<div class="track"><div class="fill" style="width:'
        f'{100.0 * rate / max_rate:.1f}%;background:{color}"></div></div>'
        f'<div class="v">{v}</div></div>')


def build_report(rows, today, n_companies):
    """Write docs/report/index.html — the shareable long-form report."""
    total = len(rows)
    ghosts = sum(1 for r in rows if int(r.get("ghost_score") or 0) >= 50)
    rate = round(100 * ghosts / total) if total else 0
    companies = {r.get("company") or "Unknown" for r in rows}

    # Ghost rate by experience level.
    lvl_stats = []
    for lvl in SENIORITY_LEVELS:
        sub = [r for r in rows if (r.get("seniority") or "mid") == lvl]
        g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
        lvl_stats.append((seniority_label(lvl), len(sub), g,
                          100.0 * g / len(sub) if sub else 0.0))
    max_lvl = max((s[3] for s in lvl_stats), default=0) or 1
    lvl_rows = "\n".join(
        barrow_html(l, "", n, g, rt, max_lvl,
                    GHOST_DEEP if rt >= 50 else (GHOST if rt >= 30 else REAL))
        for l, n, g, rt in lvl_stats)

    # Ghost rate by role (all buckets), rate desc.
    role_rows = []
    for role in sorted({r.get("role") or "other" for r in rows}):
        sub = [r for r in rows if (r.get("role") or "other") == role]
        g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
        role_rows.append((role_label(role),
                          f"../roles/{slugify(role)}/" if len(sub) >= 5 else "",
                          len(sub), g, 100.0 * g / len(sub) if sub else 0.0))
    role_rows.sort(key=lambda x: -x[4])
    max_role = max((x[4] for x in role_rows), default=0) or 1
    role_bars = "\n".join(
        barrow_html(l, href, n, g, rt, max_role,
                    GHOST_DEEP if rt >= 50 else (GHOST if rt >= 30 else REAL))
        for l, href, n, g, rt in role_rows)

    # Ghost rate by city (>= 5 postings), rate desc.
    city_rows = []
    for city in sorted({city_of(r) for r in rows}):
        sub = [r for r in rows if city_of(r) == city]
        if len(sub) < 5:
            continue
        g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
        city_rows.append((city, len(sub), g,
                          100.0 * g / len(sub) if sub else 0.0))
    city_rows.sort(key=lambda x: -x[3])
    city_slugs = company_slugs([c for c, _, _, _ in city_rows])
    max_city = max((x[3] for x in city_rows), default=0) or 1
    city_bars = "\n".join(
        barrow_html(c, f"../cities/{city_slugs[c]}/", n, g, rt, max_city,
                    GHOST_DEEP if rt >= 50 else (GHOST if rt >= 30 else REAL))
        for c, n, g, rt in city_rows)

    # Top 10 ghostiest companies by suspected-ghost count.
    by_company = {}
    for r in rows:
        c = r.get("company") or "Unknown"
        by_company.setdefault(c, []).append(r)
    co_rows = []
    for c, sub in by_company.items():
        g = sum(1 for r in sub if int(r.get("ghost_score") or 0) >= 50)
        co_rows.append((c, len(sub), g,
                        100.0 * g / len(sub) if sub else 0.0))
    co_rows.sort(key=lambda x: (-x[2], -x[1]))
    co_slugs = company_slugs([c for c, _, _, _ in co_rows])
    max_co = max((x[2] for x in co_rows[:10]), default=0) or 1
    co_bars = "\n".join(
        f'<div class="barrow"><div class="n">'
        f'<a href="../companies/{co_slugs[c]}/">{html.escape(c)}</a></div>'
        f'<div class="track"><div class="fill" style="width:'
        f'{100.0 * g / max_co:.1f}%;background:{GHOST}"></div></div>'
        f'<div class="v"><b>{g:,}</b> of {n:,} &middot; {rt:.0f}%</div></div>'
        for c, n, g, rt in co_rows[:10])

    ghostiest_role = role_rows[0] if role_rows else ("—", "", 0, 0, 0)
    ghostiest_city = city_rows[0] if city_rows else ("—", 0, 0, 0)
    entry = next((s for s in lvl_stats if s[0] == "Entry-level"),
                 ("Entry-level", 0, 0, 0))

    doc_title = (f"Ghost Jobs Report 2026: {rate}% of Tech Job Postings Are "
                 f"Ghosts \u2014 Ghost Job Tracker")
    meta_desc = (f"We tracked {total:,} job postings at {len(companies)} US tech "
                 f"companies. {rate}% show ghost signals: stale listings and "
                 f"reposts. Full breakdown by role, city, and experience level.")
    og_url = f"{SITE_URL}/report/"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
{page_head(doc_title, meta_desc, og_url, og_type="article")}
</head>
<body>
{site_nav(home_prefix="../")}
<header class="report-hero">
  <div class="wrap-narrow" style="position:relative;z-index:1;">
    <p class="eyebrow" style="color:#F2B8B2;"><span class="dot"></span>Ghost Jobs Report &middot; 2026</p>
    <div class="bignum">{rate}%</div>
    <h1>of tech job postings are ghosts.</h1>
    <p class="lede">We tracked {total:,} job postings across {len(companies)} US tech
    companies, day after day. {ghosts:,} of them show ghost signals &mdash; listings
    that stay up for months or get quietly reposted under new IDs. Here is the
    full breakdown, free to share with attribution.</p>
    <p class="dateline">Data as of {today} &middot; updated daily</p>
  </div>
</header>

<div class="wrap-narrow">
  <div class="section" style="padding:56px 0 8px;">
    <div class="kpis" style="grid-template-columns:repeat(2,1fr);">
      <div class="kpi"><div class="v" style="color:{GHOST_DEEP};">{ghostiest_role[4]:.0f}%</div>
        <div class="l">ghost rate for <b>{html.escape(ghostiest_role[0])}</b> roles &mdash; the highest of any role</div></div>
      <div class="kpi"><div class="v" style="color:{GHOST_DEEP};">{ghostiest_city[3]:.0f}%</div>
        <div class="l">ghost rate in <b>{html.escape(ghostiest_city[0])}</b> &mdash; the highest of any metro</div></div>
      <div class="kpi"><div class="v" style="color:{REAL};">{entry[3]:.0f}%</div>
        <div class="l">ghost rate for entry-level postings &mdash; the lowest of any level</div></div>
      <div class="kpi"><div class="v">{total:,}</div>
        <div class="l">postings tracked daily across {len(companies)} companies</div></div>
    </div>
  </div>

  <div class="section" style="padding:48px 0 8px;">
    <div class="pullquote">
      <div class="big">{ghostiest_role[4]:.0f}% of {html.escape(ghostiest_role[0].lower())} postings look like ghosts.</div>
      <div class="cap">Product roles are the ghost-job capital of the market &mdash;
      {ghostiest_role[3]:,} of {ghostiest_role[2]:,} tracked {html.escape(ghostiest_role[0].lower())}
      listings show ghost signals.</div>
    </div>
  </div>

  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">By experience level</p>
      <h2>Mid-level roles carry the most ghosts</h2>
      <p>Entry-level postings are the least likely to be ghosts &mdash; internships
      are real hiring. The ghost economy lives in the middle of the ladder.</p>
    </div>
    {lvl_rows}
  </div>

  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">By role</p>
      <h2>Which jobs are most haunted</h2>
      <p>Click a role for its full ghost-job breakdown.</p>
    </div>
    {role_bars}
  </div>

  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">By city</p>
      <h2>Where the ghosts cluster</h2>
      <p>Metros with at least 5 tracked postings. Click for the full breakdown.</p>
    </div>
    {city_bars}
  </div>

  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow">By company</p>
      <h2>The 10 ghostiest companies</h2>
      <p>Ranked by number of suspected ghost postings.</p>
    </div>
    {co_bars}
  </div>

  <div class="section" style="padding:40px 0;">
    <div class="sec-head">
      <p class="sec-eyebrow blue">Methodology</p>
      <h2>How we score ghost jobs</h2>
      <p>Every day we snapshot the job boards and record which postings are still listed.</p>
    </div>
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
    <p class="disclaimer">Heuristics based on public posting data, not an accusation
    against any employer &mdash; some roles are simply evergreen or hard to fill.</p>
  </div>

  <div class="section" style="padding:24px 0 72px;">
    <div class="newsletter" id="newsletter">
      <h2>Get the real jobs, skip the ghosts</h2>
      <p>A free daily digest of genuinely-new postings. No ghost jobs, no spam.</p>
      <form action="{SIGNUP_FORM_ACTION}" method="post">
        <input type="email" name="email" placeholder="you@example.com" required
               aria-label="Email address">
        <button type="submit">Notify me</button>
      </form>
      <p class="fineprint">Free forever. Unsubscribe anytime.</p>
    </div>
  </div>
</div>
{site_footer(n_companies, today, home_prefix="../")}
</body>
</html>
"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"report -> {path} (ghost rate {rate}%)")
    return {"rate": rate, "total": total, "ghosts": ghosts}


# ---------------------------------------------------------------------------
# Sitemap / robots / digest archive
# ---------------------------------------------------------------------------

def build_sitemap(pages, role_pages, city_pages):
    """Write docs/sitemap.xml covering main, digest, company, role, city,
    and report pages."""
    today = date.today().isoformat()
    import glob
    urls = ["", "digest/", "report/"]
    for src in sorted(glob.glob(os.path.join(
            os.path.dirname(COMPANIES_DIR), "digest", "[0-9]*.html"))):
        day = os.path.basename(src)[:-len(".html")]
        urls.append(f"digest/{day}.html")
    for p in pages:
        urls.append(f"companies/{p['slug']}/")
    for p in role_pages:
        urls.append(f"roles/{p['slug']}/")
    for p in city_pages:
        urls.append(f"cities/{p['slug']}/")
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


def build_digest_archive(n_companies, today):
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

    doc_title = "Digest archive \u2014 Ghost Job Tracker"
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
{page_head(doc_title, "Every daily Real Jobs Digest: genuinely-new postings, zero ghosts.",
           f"{SITE_URL}/digest/")}
</head>
<body>
{site_nav(home_prefix="../")}
<div class="pagehead"><div class="wrap">
  <p class="crumb"><a href="../">&larr; Ghost Job Tracker</a></p>
  <h1>Digest archive</h1>
  <p class="sub">Every daily Real Jobs Digest &mdash; genuinely-new postings, zero ghosts.</p>
</div></div>
<div class="wrap-narrow">
  <ul class="dlist">
    {body}
  </ul>
</div>
{site_footer(n_companies, today, home_prefix="../")}
</body>
</html>
"""
    with open(os.path.join(DIGEST_DIR, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(page)
    print(f"digest archive: {len(entries)} digest(s) -> {DIGEST_DIR}/index.html")
    return len(entries)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def build_main(rows, role_groups, role_slugs, city_groups, city_slugs):
    total = len(rows)
    ghosts = [r for r in rows if int(r.get("ghost_score") or 0) >= 50]
    n_ghosts = len(ghosts)
    rate = round(100 * n_ghosts / total) if total else 0
    companies = {r["company"] for r in rows if r.get("company")}
    n_companies = len(companies)
    avg_days = (sum(int(r.get("days_listed") or 0) for r in rows) / total) if total else 0
    today = date.today().isoformat()

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

    # Top-10 companies by suspected ghosts -> CSS bars (no chart lib).
    by_company = {}
    for r in ghosts:
        c = r.get("company") or "Unknown"
        by_company[c] = by_company.get(c, 0) + 1
    ranked = sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    co_slugs = company_slugs([c for c, _ in ranked])
    max_co = max((n for _, n in ranked), default=0) or 1
    co_bars = "\n".join(
        barrow_html(c, f"companies/{co_slugs[c]}/", None, n, 0, max_co, GHOST)
        for c, n in ranked)

    # Company browse grid (ghosts desc).
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
        f'<b>{g["ghosts"]:,}</b> suspected ghosts</div></div>'
        for g in grid_rows)

    # Compact role / city browse grids.
    def tag_grid(groups, gslugs, label_fn, url_prefix):
        tags = []
        order = sorted(groups,
                       key=lambda k: (-sum(1 for r in groups[k]
                                          if int(r.get("ghost_score") or 0) >= 50),
                                      -len(groups[k])))
        for key in order:
            n = len(groups[key])
            g = sum(1 for r in groups[key]
                    if int(r.get("ghost_score") or 0) >= 50)
            tags.append(
                f'<a class="tag" href="{url_prefix}{gslugs[key]}/">'
                f'<b>{html.escape(label_fn(key))}</b>'
                f'<span>{n:,} postings &middot; {g:,} ghosts</span></a>')
        return "\n".join(tags)

    role_tags = tag_grid(role_groups, role_slugs, role_label, "roles/")
    city_tags = tag_grid(city_groups, city_slugs, lambda c: c, "cities/")

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
        barrow_html(s["label"], "", s["total"], s["ghosts"], s["rate"],
                    max_rate, GHOST_DEEP if s["rate"] >= 50
                    else (GHOST if s["rate"] >= 30 else REAL))
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
        f'{html.escape(t["label"])}<span class="cnt">{t["total"]:,}</span></button>'
        for t in real_tabs)

    def tab_panel(t):
        if t["rows"]:
            body = "\n".join(real_job_row(r) for r in t["rows"])
            note = (f'<p class="tab-note">Showing the freshest 100 of '
                    f'{t["total"]:,} {html.escape(t["label"].lower())} openings.</p>'
                    if t["total"] > 100 else "")
            inner = (f'<div class="table-wrap"><table class="data">\n'
                     "<thead><tr><th>Job title</th><th>Company</th><th>Location</th>"
                     '<th class="num">Days listed</th><th class="num">Freshness</th>'
                     "<th>Apply</th></tr></thead>\n<tbody>\n" + body +
                     "\n</tbody>\n</table></div>" + note)
        else:
            inner = ('<p class="none">No verified-fresh openings at this level '
                     "right now.</p>")
        active = " active" if t["lvl"] == "mid" else ""
        return (f'<div class="tab-panel{active}" id="tab-{t["lvl"]}" '
                f'role="tabpanel">\n{inner}\n</div>')

    tab_panels = "\n".join(tab_panel(t) for t in real_tabs)

    doc_title = "Ghost Job Tracker \u2014 Find the Real Jobs, Skip the Ghosts"
    meta_desc = (f"We track {total:,} job postings across {n_companies} US tech "
                 f"companies daily. {rate}% show ghost signals. Browse verified-fresh "
                 f"openings and the ghost watchlist, free.")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{page_head(doc_title, meta_desc, SITE_URL + "/")}
</head>
<body>
{site_nav()}

<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow"><span class="dot"></span>Tracking {total:,} postings &middot; updated {today}</p>
    <h1><span class="stat">{rate}%</span> of tech job postings are ghosts.</h1>
    <p class="lede">We snapshot the job boards of {n_companies} US tech companies
    every single day and score each posting for ghost signals &mdash; stale listings
    that never hire, quietly reposted under new IDs. This is what the data says,
    and where the real jobs are.</p>
    <div class="hero-ctas">
      <form class="signup-inline" action="{SIGNUP_FORM_ACTION}" method="post">
        <input type="email" name="email" placeholder="you@example.com" required
               aria-label="Email address">
        <button type="submit">Get the free digest</button>
      </form>
      <a class="btn btn-outline" style="color:#fff;border-color:rgba(255,255,255,.3);" href="#real-jobs">Browse real jobs &darr;</a>
    </div>
    <div class="kpi-strip">
      <div class="kpi-dark"><div class="v">{total:,}</div><div class="l">postings tracked daily</div></div>
      <div class="kpi-dark"><div class="v red">{n_ghosts:,}</div><div class="l">suspected ghost jobs</div></div>
      <div class="kpi-dark"><div class="v">{avg_days:,.0f} days</div><div class="l">average time listed</div></div>
      <div class="kpi-dark"><div class="v green">{n_companies}</div><div class="l">companies tracked</div></div>
    </div>
  </div>
</header>

<div class="section" id="ghost-rate">
  <div class="wrap">
    <div class="sec-head">
      <p class="sec-eyebrow">The problem</p>
      <h2>Ghost rate by experience level</h2>
      <p>Share of postings with a ghost score of 50+, per seniority band.
      Entry-level postings are the least likely to be ghosts &mdash; the ghost
      economy lives in the middle of the ladder.</p>
    </div>
    {lvl_rows}
  </div>
</div>

<div class="section alt" id="watchlist">
  <div class="wrap">
    <div class="sec-head">
      <p class="sec-eyebrow">The evidence</p>
      <h2>Ghost watchlist</h2>
      <p>Every posting showing ghost signals, ranked by ghost score. Search,
      filter by level, or click a column to sort.</p>
    </div>
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
      <table class="data" id="watch">
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
  </div>
</div>

<div class="section" id="real-jobs">
  <div class="wrap">
    <div class="sec-head">
      <p class="sec-eyebrow green">The solution</p>
      <h2>Real jobs by experience level</h2>
      <p>Postings with a ghost score under {REAL_THRESHOLD} &mdash; no 90-day stale
      listings, no reposts. Freshest first.</p>
    </div>
    <div class="tabs" role="tablist">
      {tab_btns}
    </div>
    {tab_panels}
  </div>
</div>

<div class="section alt" id="companies">
  <div class="wrap">
    <div class="sec-head">
      <p class="sec-eyebrow">By company</p>
      <h2>Suspected ghosts by company</h2>
      <p>Postings with a ghost score of 50 or more, per company. Click through
      for each company's full breakdown.</p>
    </div>
    {co_bars}
    <div class="sec-head" style="margin-top:48px;">
      <h2 style="font-size:1.4rem;">Browse all {n_companies} companies</h2>
    </div>
    <div class="cogrid">
      {grid_html}
    </div>
    <div class="sec-head" style="margin-top:48px;">
      <h2 style="font-size:1.4rem;">Browse by role</h2>
      <p>Ghost-job stats per role family.</p>
    </div>
    <div class="taglist">
      {role_tags}
    </div>
    <div class="sec-head" style="margin-top:40px;">
      <h2 style="font-size:1.4rem;">Browse by city</h2>
      <p>Ghost-job stats per metro.</p>
    </div>
    <div class="taglist">
      {city_tags}
    </div>
  </div>
</div>

<div class="wrap" id="report">
  <div class="section" style="padding-bottom:0;">
    <div class="promo">
      <div>
        <h2>The Ghost Jobs Report</h2>
        <p>{n_ghosts:,} of {total:,} tracked postings ({rate}%) look like ghosts.
        The full shareable breakdown &mdash; by role, city, and experience level.</p>
        <p><a class="btn btn-ghost-red" href="report/">Read the report &rarr;</a></p>
      </div>
      <div class="bignum">{rate}%<small>ghost rate across {n_companies} companies</small></div>
    </div>
  </div>
</div>

<div class="section" id="how-it-works">
  <div class="wrap-narrow">
    <div class="sec-head">
      <p class="sec-eyebrow blue">Methodology</p>
      <h2>How it works</h2>
      <p>Every day we snapshot the job boards of {n_companies} US tech companies
      and record which postings are still listed. A posting earns ghost points
      when it stays up for a long time or keeps getting reposted under a new
      listing ID:</p>
    </div>
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
    <p class="disclaimer">These are heuristics based on public posting data, not an
    accusation against any employer &mdash; some roles are simply evergreen or hard to fill.</p>
  </div>
</div>

<div class="wrap" id="newsletter">
  <div class="section" style="padding-top:0;">
    <div class="newsletter">
      <h2>Get the real jobs, skip the ghosts</h2>
      <p>A free daily digest of genuinely-new postings &mdash; no ghost jobs, no spam.
      Browse the <a href="digest/" style="color:#175CD3;font-weight:600;">digest archive</a>.</p>
      <form action="{SIGNUP_FORM_ACTION}" method="post">
        <input type="email" name="email" placeholder="you@example.com" required
               aria-label="Email address">
        <button type="submit">Notify me</button>
      </form>
      <p class="fineprint">Free forever. Unsubscribe anytime.</p>
    </div>
  </div>
</div>

{site_footer(n_companies, today)}

<script>
var DATA = {data_json};

function esc(s) {{
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {{
    return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c];
  }});
}}
function scoreColor(s) {{
  if (s >= 75) return "{GHOST_DEEP}";
  if (s >= 50) return "{GHOST}";
  return "{REAL}";
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
      "<td class=\\"num\\"><span class=\\"scorebar\\"><span class=\\"track\\">" +
        "<span class=\\"fill\\" style=\\"display:block;width:" + Math.min(r.score,100) +
        "%;background:" + scoreColor(r.score) + "\\"></span></span>" +
        "<span class=\\"n\\">" + r.score + "</span></span></td>" +
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
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    rows = load_rows()
    for r in rows:
        r["role"] = classify_role(r.get("title"))
    role_groups = group_rows(rows, lambda r: r.get("role") or "other", min_n=5)
    city_groups = group_rows(rows, city_of, min_n=5)
    role_slugs = company_slugs(role_groups)
    city_slugs = company_slugs(city_groups)
    n_companies = len({r.get("company") for r in rows if r.get("company")})
    today = date.today().isoformat()

    page = build_main(rows, role_groups, role_slugs, city_groups, city_slugs)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {OUT_PATH} ({len(page):,} bytes, {len(rows)} postings)")
    build_digest_archive(n_companies, today)
    company_pages = build_company_pages(rows, n_companies)
    role_pages = build_role_pages(role_groups, role_slugs, today, n_companies)
    city_pages = build_city_pages(city_groups, city_slugs, today, n_companies)
    build_report(rows, today, n_companies)
    build_sitemap(company_pages, role_pages, city_pages)
    build_robots()


if __name__ == "__main__":
    main()
