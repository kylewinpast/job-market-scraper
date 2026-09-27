"""Classify a job title into a role bucket.

Buckets: data, engineering, product, design, sales, marketing, operations,
finance, people, legal, support, other.

Rules (case-insensitive, first match wins in the order below). The title is
first normalized with ghost.normalize_title (lowercased, parentheticals and
trailing " - location" stripped).

- data:        "data scientist", "data analyst", "data engineer",
               "data architect", "machine learning", "ml engineer",
               "business intelligence", "bi" (standalone), "analytics",
               "research scientist"
- engineering: engineer/engineering, developer, software, swe, devops, sre,
               qa (standalone), mobile, front/back/full-stack, infrastructure,
               architect
- product:     "product manager", pm (standalone)
- design:      designer, "product design", ux, ui (standalone)
- sales:       sales, "account executive", sdr, bdr, revenue
- marketing:   marketing, growth, seo, content
- operations:  operations, ops (standalone), "program manager",
               "chief of staff"
- finance:     finance, financial, accounting, treasury, analyst
               ("Data Analyst" is caught by data first, so bare "analyst"
               here mostly means financial/business/deal-desk analysts)
- people:      recruiter/recruiting, hr (standalone), people, talent
- legal:       legal, counsel, attorney
- support:     "customer success", support
- default:     other

Priority notes: data beats engineering ("Data Engineer" is data, not
engineering); product only matches "product manager"/pm so "Product
Designer" falls through to design; bare "analyst" lands in finance only
after the data bucket has claimed data analysts.

Stdlib only.
"""
import re

from ghost import normalize_title

ROLES = ("data", "engineering", "product", "design", "sales", "marketing",
         "operations", "finance", "people", "legal", "support", "other")
LABELS = {
    "data": "Data",
    "engineering": "Engineering",
    "product": "Product",
    "design": "Design",
    "sales": "Sales",
    "marketing": "Marketing",
    "operations": "Operations",
    "finance": "Finance",
    "people": "People",
    "legal": "Legal",
    "support": "Support",
    "other": "Other",
}

_RULES = [
    ("data", [
        r"\bdata (scientist|analyst|engineer|architect)\b",
        r"\bmachine learning\b",
        r"\bml engineer\b",
        r"\bbusiness intelligence\b",
        r"\bbi\b",
        r"\banalytics\b",
        r"\bresearch scientist\b",
    ]),
    ("engineering", [
        r"\bengineer(ing)?\b",
        r"\bdeveloper\b",
        r"\bsoftware\b",
        r"\bswe\b",
        r"\bdevops\b",
        r"\bsre\b",
        r"\bqa\b",
        r"\bmobile\b",
        r"\bfront[\s-]?end\b",
        r"\bback[\s-]?end\b",
        r"\bfull[\s-]?stack\b",
        r"\binfrastructure\b",
        r"\barchitect\b",
    ]),
    ("product", [
        r"\bproduct manager\b",
        r"\bpm\b",
    ]),
    ("design", [
        r"\bdesigner\b",
        r"\bproduct design\b",
        r"\bux\b",
        r"\bui\b",
    ]),
    ("sales", [
        r"\bsales\b",
        r"\baccount executive\b",
        r"\bsdr\b",
        r"\bbdr\b",
        r"\brevenue\b",
    ]),
    ("marketing", [
        r"\bmarketing\b",
        r"\bgrowth\b",
        r"\bseo\b",
        r"\bcontent\b",
    ]),
    ("operations", [
        r"\boperations\b",
        r"\bops\b",
        r"\bprogram manager\b",
        r"\bchief of staff\b",
    ]),
    ("finance", [
        r"\bfinance\b",
        r"\bfinancial\b",
        r"\baccounting\b",
        r"\btreasury\b",
        r"\banalyst\b",
    ]),
    ("people", [
        r"\brecruit(er|ing)?\b",
        r"\bhr\b",
        r"\bpeople\b",
        r"\btalent\b",
    ]),
    ("legal", [
        r"\blegal\b",
        r"\bcounsel\b",
        r"\battorney\b",
    ]),
    ("support", [
        r"\bcustomer success\b",
        r"\bsupport\b",
    ]),
]

_COMPILED = [(bucket, [re.compile(p) for p in pats]) for bucket, pats in _RULES]


def classify(title):
    """Return a role bucket code for a job title."""
    t = normalize_title(title or "")
    for bucket, rxs in _COMPILED:
        for rx in rxs:
            if rx.search(t):
                return bucket
    return "other"


def role_label(role):
    """Display label for a role code, e.g. 'data' -> 'Data'."""
    return LABELS.get(role, "Other")


def main():
    import sys
    for line in sys.stdin:
        line = line.rstrip("\n")
        if line.strip():
            role = classify(line)
            print(f"{role:11s}  {line}")


if __name__ == "__main__":
    main()
