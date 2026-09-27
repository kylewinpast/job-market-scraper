"""Build the Job Market Dashboard .pbix programmatically (no Power BI Desktop needed).

Pipeline: jobs_export.csv -> Jobs + JobSkills tables -> themed report -> .pbix
"""
import csv
import json
import os
import sys
from datetime import date

import pbix_mcp.server as pbi

PROJECT = os.path.expanduser("~/workspace/projects/job-market-scraper")
CSV_PATH = os.path.join(PROJECT, "data", "jobs_export.csv")
OUT_PATH = os.path.join(PROJECT, "output", "job-market-dashboard.pbix")

PALETTE = ["#143D5E", "#1B7F79", "#E8A838", "#D95D39",
           "#6A8EA6", "#7FB069", "#5B5EA6", "#C1666B"]
NAVY = "#143D5E"
INK = "#1F2A37"
MUTED = "#5A6C7D"
PAGE_BG = "#F2F4F7"
CARD_BG = "#FFFFFF"


def check(result, step):
    text = str(result)
    if '"success":false' in text.replace(" ", "") or text.strip().lower().startswith("error"):
        print(f"FAILED [{step}]: {text[:500]}")
        sys.exit(1)
    print(f"ok [{step}]")


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_tables(rows):
    jobs_cols = [
        {"name": "url", "data_type": "String"},
        {"name": "title", "data_type": "String"},
        {"name": "company", "data_type": "String"},
        {"name": "location", "data_type": "String"},
        {"name": "source", "data_type": "String"},
        {"name": "job_type", "data_type": "String"},
        {"name": "salary", "data_type": "String"},
        {"name": "posted_at", "data_type": "String"},
        {"name": "fit_score", "data_type": "Int64"},
        {"name": "fit_reasons", "data_type": "String"},
        {"name": "skills", "data_type": "String"},
    ]
    jobs_rows, skill_rows = [], []
    for r in rows:
        jobs_rows.append({
            "url": r["url"], "title": r["title"], "company": r["company"],
            "location": r["location"], "source": r["source"],
            "job_type": r.get("job_type", ""), "salary": r.get("salary", ""),
            "posted_at": r.get("posted_at", ""),
            "fit_score": int(r["fit_score"] or 0),
            "fit_reasons": r["fit_reasons"], "skills": r["skills"],
        })
        for s in (r["skills"] or "").split("|"):
            s = s.strip()
            if s:
                skill_rows.append({"url": r["url"], "skill": s})
    tables = [
        {"name": "Jobs", "columns": jobs_cols, "rows": jobs_rows},
        {"name": "JobSkills",
         "columns": [{"name": "url", "data_type": "String"},
                     {"name": "skill", "data_type": "String"}],
         "rows": skill_rows},
    ]
    return json.dumps(tables)


def measures():
    return json.dumps([
        {"table": "Jobs", "name": "Posting count",
         "expression": "COUNTROWS(Jobs)", "format_string": "#,0"},
        {"table": "Jobs", "name": "Avg fit score",
         "expression": "AVERAGE(Jobs[fit_score])", "format_string": "#,0.0"},
        {"table": "Jobs", "name": "Top matches",
         "expression": "COUNTROWS(FILTER(Jobs, Jobs[fit_score] >= 10))",
         "format_string": "#,0"},
        {"table": "JobSkills", "name": "Skill mentions",
         "expression": "COUNTROWS(JobSkills)", "format_string": "#,0"},
    ])


def relationships():
    return json.dumps([
        {"from_table": "JobSkills", "from_column": "url",
         "to_table": "Jobs", "to_column": "url"},
    ])


def proto(table, fields):
    """Build prototypeQuery + projections pieces.

    fields: list of (role, name, kind) where kind is 'col' or 'measure'.
    Returns (projections, prototype_query).
    """
    alias = table[:1].lower()
    projections = {}
    selects = []
    for role, name, kind in fields:
        qref = f"{table}.{name}"
        projections.setdefault(role, []).append({"queryRef": qref})
        node = "Measure" if kind == "measure" else "Column"
        selects.append({
            node: {"Expression": {"SourceRef": {"Source": alias}},
                   "Property": name},
            "Name": qref,
        })
    pq = {"Version": 2,
          "From": [{"Name": alias, "Entity": table, "Type": 0}],
          "Select": selects}
    return projections, pq


def visual_config(table, fields):
    projections, pq = proto(table, fields)
    return json.dumps({"singleVisual": {"projections": projections,
                                       "prototypeQuery": pq}})


def main():
    rows = load_rows()
    print(f"loaded {len(rows)} postings")
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    if os.path.exists(OUT_PATH):
        os.remove(OUT_PATH)

    alias = "jobdash"
    check(pbi.pbix_create(OUT_PATH, alias, build_tables(rows),
                          measures(), relationships()), "create")
    check(pbi.pbix_rename_page(alias, 0, "Overview"), "rename page")
    check(pbi.pbix_format_page(
        alias, 0,
        json.dumps({"background": {"color": PAGE_BG}})), "page bg")
    check(pbi.pbix_set_theme(
        alias, json.dumps({"name": "Job Market",
                           "dataColors": PALETTE})), "theme")

    today = date.today().strftime("%b %d, %Y")
    n = 0

    def add(vtype, x, y, w, h, cfg="", sort_by="", sort_dir="desc"):
        nonlocal n
        check(pbi.pbix_add_visual(alias, 0, vtype, x, y, w, h,
                                 cfg, sort_by, sort_dir),
              f"add visual {n} ({vtype})")
        idx = n
        n += 1
        return idx

    def fmt(idx, **kw):
        check(pbi.pbix_format_visual(alias, 0, idx, json.dumps(kw)),
              f"format visual {idx}")

    card_fmt = {"background": {"color": CARD_BG},
                "border": {"show": True, "color": "#E1E6EB",
                           "width": 1, "radius": 8},
                "dropShadow": {"show": True, "color": "#0A0A0A",
                               "transparency": 85, "blur": 12,
                               "distance": 4, "angle": 90}}

    # Title
    title_cfg = json.dumps({"singleVisual": {"objects": {"general": [{
        "properties": {"paragraphs": [
            {"textRuns": [{
                "value": "Job Market Dashboard",
                "textStyle": {"fontSize": "26pt", "color": NAVY,
                              "fontWeight": "bold",
                              "fontFamily": "Segoe UI"}}]},
            {"textRuns": [{
                "value": (f"Data job postings ranked by fit  •  {today}  •  "
                          f"{len(rows)} postings"),
                "textStyle": {"fontSize": "12pt", "color": MUTED,
                              "fontFamily": "Segoe UI"}}]}]}}]}}})
    add("textbox", 24, 8, 1232, 76, title_cfg)

    # KPI cards
    c1 = add("card", 24, 96, 296, 132,
             visual_config("Jobs", [("Values", "Posting count", "measure")]))
    fmt(c1, title={"text": "Total postings", "show": True, "fontSize": 13,
                   "color": MUTED}, **card_fmt)
    c2 = add("card", 336, 96, 296, 132,
             visual_config("Jobs", [("Values", "Avg fit score", "measure")]))
    fmt(c2, title={"text": "Avg fit score", "show": True, "fontSize": 13,
                   "color": MUTED}, **card_fmt)
    c3 = add("card", 648, 96, 296, 132,
             visual_config("Jobs", [("Values", "Top matches", "measure")]))
    fmt(c3, title={"text": "Top matches (score ≥ 10)", "show": True,
                   "fontSize": 13, "color": MUTED}, **card_fmt)

    # Slicer
    s1 = add("slicer", 960, 96, 296, 132,
             visual_config("Jobs", [("Values", "location", "col")]))
    fmt(s1, title={"text": "Location", "show": True, "fontSize": 13,
                   "color": MUTED}, **card_fmt)

    # Location bar chart
    b1 = add("clusteredBarChart", 24, 244, 608, 220,
             visual_config("Jobs", [("Category", "location", "col"),
                                    ("Y", "Posting count", "measure")]),
             sort_by="Jobs.Posting count", sort_dir="desc")
    fmt(b1, title={"text": "Postings by location", "show": True,
                   "fontSize": 14, "color": NAVY},
        dataLabels={"show": True, "fontSize": 9},
        categoryAxis={"fontSize": 9, "color": INK},
        **card_fmt)

    # Skills bar chart
    b2 = add("clusteredBarChart", 648, 244, 608, 220,
             visual_config("JobSkills",
                           [("Category", "skill", "col"),
                            ("Y", "Skill mentions", "measure")]),
             sort_by="JobSkills.Skill mentions", sort_dir="desc")
    fmt(b2, title={"text": "Skill mentions", "show": True,
                   "fontSize": 14, "color": NAVY},
        dataLabels={"show": True, "fontSize": 9},
        categoryAxis={"fontSize": 9, "color": INK},
        **card_fmt)

    # Postings table
    t1 = add("table", 24, 480, 1232, 224,
             visual_config("Jobs", [("Values", "title", "col"),
                                    ("Values", "company", "col"),
                                    ("Values", "location", "col"),
                                    ("Values", "fit_score", "col")]),
             sort_by="Jobs.fit_score", sort_dir="desc")
    fmt(t1, title={"text": "Postings ranked by fit score", "show": True,
                   "fontSize": 14, "color": NAVY},
        columnHeaders={"bold": True, "fontSize": 10, "fontColor": "#FFFFFF",
                       "backColor": NAVY},
        values={"fontSize": 9, "fontColor": INK},
        grid={"gridHorizontal": True,
              "gridHorizontalColor": "#E1E6EB"},
        **card_fmt)

    # Validate measures with the built-in DAX engine
    res = pbi.pbix_evaluate_dax(
        alias, 'Posting count,Avg fit score,Top matches')
    print("dax check:", str(res)[:300])

    check(pbi.pbix_doctor(alias), "doctor")
    check(pbi.pbix_save(alias, overwrite=True), "save")
    check(pbi.pbix_close(alias), "close")
    size = os.path.getsize(OUT_PATH)
    print(f"saved {OUT_PATH} ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
