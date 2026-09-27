"""Normalize raw Greenhouse location strings to canonical metros.

Problem: the same metro appears as "Seattle, WA", "Seattle, San Francisco,
New York, US - Remote", "Seattle, WA OR New York, NY OR Remote North
America", ... — the dashboard's location chart/slicer becomes noise.
This maps every raw string to one canonical "City, ST" (or "Remote - US"),
using the FIRST recognizable metro in multi-location postings.
"""
import re

# canonical -> aliases (lowercase). Order matters for position-based matching.
CITY_ALIASES = {
    "New York, NY": ["new york city", "new york", "nyc"],
    "San Francisco, CA": ["san francisco", "sf"],
    "Seattle, WA": ["seattle", "sea"],
    "Chicago, IL": ["chicago", "chi"],
    "Boston, MA": ["boston"],
    "Denver, CO": ["denver"],
    "Austin, TX": ["austin"],
    "Bellevue, WA": ["bellevue"],
    "Menlo Park, CA": ["menlo park"],
    "Palo Alto, CA": ["palo alto"],
    "Washington, DC": ["washington, dc", "washington dc", "washington"],
    "Westlake, TX": ["westlake"],
    "Pittsburgh, PA": ["pittsburgh"],
    "Atlanta, GA": ["atlanta", "georgia"],
    # DFW (for future postings)
    "Dallas, TX": ["dallas"],
    "Plano, TX": ["plano"],
    "McKinney, TX": ["mckinney"],
    "Frisco, TX": ["frisco"],
    "Irving, TX": ["irving"],
    "Fort Worth, TX": ["fort worth"],
    "Arlington, TX": ["arlington"],
    "Richardson, TX": ["richardson"],
}

# Bare remote / country-level / unknown -> Remote - US
REMOTE_PATTERNS = ["remote", "us-rem", "us-remote", "united states",
                   r"\bus\b", r"\busa\b", r"n/a"]

# Short aliases that need word boundaries to avoid false hits
# (e.g. "sea" in "seattle" is fine, but avoid "chi" matching "chicago"? no —
# "chi" IS chicago. The risk is "sea" matching "seattle" twice; harmless.)


def _compile_aliases():
    compiled = []  # (canonical, regex)
    for canonical, aliases in CITY_ALIASES.items():
        for a in aliases:
            # multi-word aliases: plain substring is safe enough
            if " " in a or "," in a:
                pat = re.escape(a)
            else:
                pat = r"\b" + re.escape(a) + r"\b"
            compiled.append((canonical, re.compile(pat)))
    return compiled


_COMPILED = _compile_aliases()
_REMOTE_RES = [re.compile(p) for p in REMOTE_PATTERNS]


def normalize_location(raw):
    """Map a raw location string to a canonical metro or 'Remote - US'."""
    loc = (raw or "").strip().lower()
    if not loc:
        return "Remote - US"

    # Find the earliest-occurring city alias = primary metro.
    best = None  # (position, canonical)
    for canonical, rx in _COMPILED:
        m = rx.search(loc)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), canonical)
    if best:
        return best[1]

    # No city found: remote / country-level / unknown -> Remote - US
    return "Remote - US"


if __name__ == "__main__":
    tests = [
        "Seattle, WA",
        "Seattle, San Francisco, New York, US - Remote",
        "Seattle, WA OR New York, NY OR Remote North America",
        "SF, NY, Remote",
        "NYC, SF, Seattle, US",
        "SEA, SF, NYC, CHI",
        "New York, New York, USA; Pittsburgh, Pennsylvania, USA",
        "Hybrid - New York, NY",
        "Remote - USA",
        "US-REM",
        "N/A",
        "United States",
        "Chicago, IL; Denver, CO; Westlake, TX",
        "San Francisco, CA • New York, NY",
        "Austin; New York City; Palo Alto",
        "Bellevue, WA; Menlo Park, CA",
        "Westlake, TX",
        "Washington, DC",
        "US-SF, US-Seattle, US-NYC, US-Chicago, US-Georgia or US-Remote",
    ]
    for t in tests:
        print(f"{normalize_location(t):20s} <- {t}")
