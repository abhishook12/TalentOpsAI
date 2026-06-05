"""
State Normalizer Utility
========================
Normalizes raw US state strings from recruiter data into canonical full state
names. Handles abbreviations, common typos/misspellings, and flags invalid or
unrecognized entries for human review.

No external dependencies — uses only the Python standard library.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Canonical set of all 50 US states + District of Columbia
# ---------------------------------------------------------------------------
VALID_STATES: set[str] = {
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "District of Columbia",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
}

# Pre-computed lowercase → canonical lookup for case-insensitive matching
_VALID_STATES_LOWER: dict[str, str] = {s.lower(): s for s in VALID_STATES}


# ---------------------------------------------------------------------------
# Two-letter abbreviation → full state name  (all 50 states + DC)
# ---------------------------------------------------------------------------
ABBR_MAP: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

# Pre-computed lowercase → canonical for abbreviations
_ABBR_MAP_LOWER: dict[str, str] = {k.lower(): v for k, v in ABBR_MAP.items()}


# ---------------------------------------------------------------------------
# Known typos / misspellings  (lowercase key → canonical name)
# Sourced from data-analysis findings + common keyboard errors
# ---------------------------------------------------------------------------
TYPO_MAP: dict[str, str] = {
    # --- Typos explicitly found in the data analysis ---
    "caliornia": "California",
    "ilinois": "Illinois",
    "winconsin": "Wisconsin",
    "tennesse": "Tennessee",
    "new york": "New York",       # casing issue captured here too
    "new jersey": "New Jersey",   # casing issue
    "washington dc": "District of Columbia",
    "washington d.c.": "District of Columbia",
    "washington, dc": "District of Columbia",
    "washington, d.c.": "District of Columbia",
    "washington d.c": "District of Columbia",

    # --- Additional common misspellings / alternate forms ---
    # California
    "californa": "California",
    "californai": "California",
    "califorina": "California",
    "californnia": "California",
    "califronia": "California",

    # Colorado
    "colordo": "Colorado",
    "colrado": "Colorado",

    # Connecticut
    "conneticut": "Connecticut",
    "connecticutt": "Connecticut",
    "connnecticut": "Connecticut",
    "connecticut": "Connecticut",  # correct spelling (acts as passthrough)
    "conneticutt": "Connecticut",

    # Delaware
    "delware": "Delaware",

    # Florida
    "florda": "Florida",
    "flordia": "Florida",
    "flordia": "Florida",

    # Georgia
    "goergia": "Georgia",
    "gerogia": "Georgia",

    # Hawaii
    "hawai": "Hawaii",
    "hawii": "Hawaii",

    # Idaho
    "idahoe": "Idaho",

    # Illinois
    "illinios": "Illinois",
    "illinos": "Illinois",
    "illinoi": "Illinois",
    "illionis": "Illinois",
    "illinoise": "Illinois",

    # Indiana
    "indana": "Indiana",
    "indianna": "Indiana",

    # Kansas
    "kanas": "Kansas",

    # Kentucky
    "kentuky": "Kentucky",
    "kentuckey": "Kentucky",

    # Louisiana
    "louisianna": "Louisiana",
    "louisana": "Louisiana",

    # Maine
    "miane": "Maine",

    # Maryland
    "maryalnd": "Maryland",
    "marlyand": "Maryland",

    # Massachusetts
    "massachusets": "Massachusetts",
    "massachussetts": "Massachusetts",
    "massachsuetts": "Massachusetts",
    "masachusetts": "Massachusetts",
    "massachusettes": "Massachusetts",
    "massachuetts": "Massachusetts",
    "massachussets": "Massachusetts",

    # Michigan
    "michgan": "Michigan",
    "michagan": "Michigan",

    # Minnesota
    "minnnesota": "Minnesota",
    "minesota": "Minnesota",
    "minnesotta": "Minnesota",

    # Mississippi
    "missisippi": "Mississippi",
    "mississipi": "Mississippi",
    "missippi": "Mississippi",
    "mississppi": "Mississippi",

    # Missouri
    "misouri": "Missouri",
    "missori": "Missouri",

    # Montana
    "montanna": "Montana",
    "monatna": "Montana",

    # Nebraska
    "nebraksa": "Nebraska",

    # Nevada
    "nevda": "Nevada",

    # New Hampshire
    "new hampshire": "New Hampshire",  # casing
    "new hamshire": "New Hampshire",
    "newhampshire": "New Hampshire",

    # New Jersey
    "newjersey": "New Jersey",
    "new jersy": "New Jersey",

    # New Mexico
    "new mexico": "New Mexico",
    "newmexico": "New Mexico",
    "new mexcio": "New Mexico",

    # New York
    "newyork": "New York",
    "new yrok": "New York",

    # North Carolina
    "north carolina": "North Carolina",
    "northcarolina": "North Carolina",
    "n. carolina": "North Carolina",
    "n carolina": "North Carolina",
    "north carlina": "North Carolina",

    # North Dakota
    "north dakota": "North Dakota",
    "northdakota": "North Dakota",
    "n. dakota": "North Dakota",
    "n dakota": "North Dakota",

    # Ohio
    "ohi": "Ohio",

    # Oklahoma
    "oklahom": "Oklahoma",

    # Oregon
    "oregeon": "Oregon",
    "orgon": "Oregon",

    # Pennsylvania
    "pennsylvnia": "Pennsylvania",
    "pennyslvania": "Pennsylvania",
    "pensylvania": "Pennsylvania",
    "pennslvania": "Pennsylvania",
    "pennsylvannia": "Pennsylvania",
    "pensilvania": "Pennsylvania",

    # Rhode Island
    "rhode island": "Rhode Island",
    "rhodeisland": "Rhode Island",
    "rhode iland": "Rhode Island",

    # South Carolina
    "south carolina": "South Carolina",
    "southcarolina": "South Carolina",
    "s. carolina": "South Carolina",
    "s carolina": "South Carolina",
    "south carlina": "South Carolina",

    # South Dakota
    "south dakota": "South Dakota",
    "southdakota": "South Dakota",
    "s. dakota": "South Dakota",
    "s dakota": "South Dakota",

    # Tennessee
    "tennesee": "Tennessee",
    "tenessee": "Tennessee",
    "tennessea": "Tennessee",
    "tenneessee": "Tennessee",

    # Texas
    "texa": "Texas",
    "texs": "Texas",
    "texsa": "Texas",

    # Utah — rarely misspelled

    # Vermont
    "vermon": "Vermont",

    # Virginia
    "virgina": "Virginia",
    "virgnia": "Virginia",

    # Washington
    "washingon": "Washington",
    "washignton": "Washington",
    "washtington": "Washington",

    # West Virginia
    "west virginia": "West Virginia",
    "westvirginia": "West Virginia",
    "w. virginia": "West Virginia",
    "w virginia": "West Virginia",
    "west virgina": "West Virginia",

    # Wisconsin
    "wisconson": "Wisconsin",
    "wiscosin": "Wisconsin",
    "winsconsin": "Wisconsin",

    # Wyoming
    "wyomng": "Wyoming",

    # District of Columbia alternates
    "d.c.": "District of Columbia",
    "d.c": "District of Columbia",
    "district of columbia": "District of Columbia",
}


# ---------------------------------------------------------------------------
# Strings that are clearly *not* a US state (country names, etc.)
# ---------------------------------------------------------------------------
_INVALID_ENTRIES: set[str] = {
    "usa",
    "us",
    "u.s.",
    "u.s.a.",
    "united states",
    "united states of america",
    "america",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "other",
    "-",
    "--",
    ".",
    "",
}


# ===================================================================
# Public API
# ===================================================================

def normalize_state_name(raw: str) -> tuple[str | None, bool, str | None]:
    """Normalize a raw state string into its canonical full name.

    Parameters
    ----------
    raw : str
        The raw state value from the source data.

    Returns
    -------
    tuple[str | None, bool, str | None]
        (normalized_state, needs_review, review_reason)

        * If the state is valid or correctable:
          ``("California", False, None)``
        * If the input is clearly invalid (country name, empty, etc.):
          ``(None, True, "invalid_state")``
        * If the input cannot be matched:
          ``(original_trimmed, True, "unrecognized_state")``
    """
    if not isinstance(raw, str):
        return (None, True, "invalid_state")

    cleaned = raw.strip()
    if not cleaned:
        return (None, True, "invalid_state")

    lower = cleaned.lower()

    # 1. Check for known-invalid entries
    if lower in _INVALID_ENTRIES:
        return (None, True, "invalid_state")

    # 2. Exact match (case-insensitive) against valid state names
    if lower in _VALID_STATES_LOWER:
        return (_VALID_STATES_LOWER[lower], False, None)

    # 3. Two-letter abbreviation
    if lower in _ABBR_MAP_LOWER:
        return (_ABBR_MAP_LOWER[lower], False, None)

    # 4. Known typo / misspelling
    if lower in TYPO_MAP:
        return (TYPO_MAP[lower], False, None)

    # 5. Unrecognized — flag for review
    return (cleaned, True, "unrecognized_state")


def is_valid_state(s: str) -> bool:
    """Return True if *s* is a correctly-spelled canonical US state name."""
    if not isinstance(s, str):
        return False
    return s.strip() in VALID_STATES
