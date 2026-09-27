"""Classify a job title into an experience level (seniority).

Levels: entry, mid, senior, exec.

Rules (case-insensitive, checked in priority order exec -> senior ->
entry -> mid). The title is first normalized with ghost.normalize_title
(lowercased, parentheticals stripped).

- exec:    chief, cto/cfo/ceo/coo/cio, [se]vp, "vice president", president,
           founder, director, "head of", "general partner"/"managing partner"
- senior:  senior, sr., staff, principal, lead, manager, distinguished, fellow
- entry:   intern, junior, jr., associate, entry, "new grad"/"recent grad"/
           "university grad", standalone roman-numeral I ("Analyst I",
           "Level I")
- default: mid

Priority notes: "Senior Director" and "Associate Director" both land in
exec (director-level). "Staff" beats "junior" if both ever appear together
(rare). Everything without a marker is mid — that is where most postings
land, which matches how boards are written.

Stdlib only.
"""
import re

from ghost import normalize_title

LEVELS = ("entry", "mid", "senior", "exec")
LABELS = {
    "entry": "Entry-level",
    "mid": "Mid-level",
    "senior": "Senior",
    "exec": "Executive",
}

_EXEC_RES = [
    r"\bchief\b",
    r"\bct[oe]o\b",          # cto, ceo
    r"\bcfo\b",
    r"\bcio\b",
    r"\bcoo\b",
    r"\b[se]?vp\b",          # vp, svp, evp
    r"\bvice president\b",
    r"\bpresident\b",
    r"\bfounder\b",
    r"\bdirector\b",
    r"\bhead of\b",
    r"\b(general|managing) partner\b",
]
_SENIOR_RES = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead(?:er)?\b",
    r"\bmanager\b",
    r"\bdistinguished\b",
    r"\bfellow\b",
]
_ENTRY_RES = [
    r"\bintern",
    r"\bjunior\b",
    r"\bjr\.?\b",
    r"\bassociate\b",
    r"\bentry\b",
    r"\b(new|recent|university) grad",
    r"\bi\b",                # standalone roman numeral I: "Analyst I", "Level I"
]

_EXEC = [re.compile(p) for p in _EXEC_RES]
_SENIOR = [re.compile(p) for p in _SENIOR_RES]
_ENTRY = [re.compile(p) for p in _ENTRY_RES]


def classify(title):
    """Return one of 'entry', 'mid', 'senior', 'exec' for a job title."""
    t = normalize_title(title or "")
    for rx in _EXEC:
        if rx.search(t):
            return "exec"
    for rx in _SENIOR:
        if rx.search(t):
            return "senior"
    for rx in _ENTRY:
        if rx.search(t):
            return "entry"
    return "mid"


def seniority_label(level):
    """Display label for a level code, e.g. 'entry' -> 'Entry-level'."""
    return LABELS.get(level, "Mid-level")


def main():
    import sys
    for line in sys.stdin:
        line = line.rstrip("\n")
        if line.strip():
            lvl = classify(line)
            print(f"{lvl:6s}  {line}")


if __name__ == "__main__":
    main()
