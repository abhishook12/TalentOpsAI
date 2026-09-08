"""
Universal Title Normalization, Seniority Leveling & Domain Specialization Engine.

Provides deep semantic classification for candidate and recruiter job titles:
1. Canonical Title Synthesis: Cleans noise, buzzwords, gimmicks, and degrees.
2. Hierarchical Seniority Level:
   - ENTRY (1) -> Entry-Level, Campus, Associate, Coordinator, Intern (Legacy: 'Campus')
   - MID (2) -> Recruiter, Specialist, Consultant (Legacy: 'Specialist')
   - SENIOR (3) -> Senior, Sr., Advanced (Legacy: 'Senior')
   - LEAD_STAFF (4) -> Lead, Principal, Staff, Manager, Founding (Legacy: 'Lead')
   - DIRECTOR (5) -> Director, Senior Director (Legacy: 'Executive')
   - VP_EXECUTIVE (6) -> VP, Head of, Chief, Partner, Founder (Legacy: 'Executive')
3. Domain Specialization:
   - TECHNICAL (Software, Engineering, AI/ML, Cloud, Data, Cyber)
   - GTM_SALES (Sales, BD, Marketing, RevOps, Growth)
   - EXECUTIVE_SEARCH (Executive Search, Leadership, Board Practice)
   - HEALTHCARE (Clinical, Nursing, Medical, Pharma, Biotech)
   - FINANCE_LEGAL (Finance, Accounting, Legal, Compliance)
   - OPERATIONS_GENERAL (Talent Acquisition, People Ops, HR)
4. Role Family: RECRUITER, SOURCER, TALENT_OPS, HR_PEOPLE, EXECUTIVE
"""

import re
from typing import Dict, Any, Optional, Tuple

# Seniority Level Definitions & Metadata
SENIORITY_RANKS = {
    "ENTRY": 1,
    "MID": 2,
    "SENIOR": 3,
    "LEAD_STAFF": 4,
    "DIRECTOR": 5,
    "VP_EXECUTIVE": 6,
}

SENIORITY_LEGACY_MAP = {
    "ENTRY": "Campus",
    "MID": "Specialist",
    "SENIOR": "Senior",
    "LEAD_STAFF": "Lead",
    "DIRECTOR": "Executive",
    "VP_EXECUTIVE": "Executive",
}

LEGACY_TO_SENIORITY_MAP = {
    "campus": "ENTRY",
    "specialist": "MID",
    "senior": "SENIOR",
    "lead": "LEAD_STAFF",
    "executive": "VP_EXECUTIVE",
    "entry": "ENTRY",
    "mid": "MID",
    "director": "DIRECTOR",
    "lead_staff": "LEAD_STAFF",
    "vp_executive": "VP_EXECUTIVE",
}

SPECIALIZATION_LABELS = {
    "TECHNICAL": "Technical & Engineering",
    "GTM_SALES": "Go-To-Market & Sales",
    "EXECUTIVE_SEARCH": "Executive Search & Leadership",
    "HEALTHCARE": "Healthcare & Clinical",
    "FINANCE_LEGAL": "Finance, Accounting & Legal",
    "OPERATIONS_GENERAL": "Talent & People Operations",
}

# Buzzword & gimmick replacements
BUZZWORD_STRIP_RE = re.compile(
    r"\b(?:ninja|rockstar|guru|wizard|champion|hero|maven|jedi|enthusiast|evangelist|magician|superhero|overlord)\b",
    re.IGNORECASE,
)

# Degrees & certifications to strip from job title strings
CREDENTIALS_STRIP_RE = re.compile(
    r"(?:,\s*|\s+[-–|]\s*)(?:MBA|SPHR|PHR|SHRM-CP|SHRM-SCP|PMP|PhD|CPA|MS|BS|BA|JD|MD|CIPD)\b",
    re.IGNORECASE,
)

# Status and tag noise
STATUS_TAG_STRIP_RE = re.compile(
    r"[\(\[\{](?:we'?re\s*(?:actively\s*)?hiring|actively\s*hiring|hiring|open\s*to\s*work|open\s*to\s*new\s*opportunities|seeking\s*opportunities|looking\s*for\s*roles|ex-[\w\s]+)[\)\]\}]|#opentowork|#hiring",
    re.IGNORECASE,
)

# Emojis and miscellaneous non-text artifacts
EMOJI_CLEAN_RE = re.compile(r"[^\w\s\.\,\-\/\&\'\(\)]")


def strip_title_noise(raw_title: Optional[str]) -> str:
    """Removes emojis, UI buzzwords, credentials, status tags, and employer company suffixes."""
    if not raw_title or not isinstance(raw_title, str):
        return ""

    title = raw_title.strip()

    # 1. Remove status tags & hashtags
    title = STATUS_TAG_STRIP_RE.sub("", title)

    # 2. Remove appended credentials (e.g. "Senior Recruiter, MBA, SPHR")
    title = CREDENTIALS_STRIP_RE.sub("", title)

    # 3. Strip employer split if '@ Company' or 'at Company'
    at_match = re.search(r"\s+(?:@|at)\s+[\w\s\.\,\&\'-]+$", title, re.IGNORECASE)
    if at_match:
        title = title[:at_match.start()].strip()

    # 4. If pipe/hyphen separated, remove slogan parts (e.g. "Ex-Google", "We build teams", "Hiring Engineers")
    if " | " in title or " – " in title:
        parts = re.split(r"\s+[\|–]\s+", title)
        filtered = [p for p in parts if not re.search(r"\b(?:ex-|we\s*build|hiring|passion|helping)\b", p, re.IGNORECASE)]
        title = " | ".join(filtered) if filtered else parts[0]

    # 5. Remove gimmicks / buzzwords
    title = BUZZWORD_STRIP_RE.sub("", title)

    # 6. Remove non-title symbols and clean whitespace
    title = EMOJI_CLEAN_RE.sub(" ", title)
    title = re.sub(r"\s+", " ", title).strip()

    # 7. Strip trailing punctuation
    title = re.sub(r"[,\|\-–\.\s]+$", "", title).strip()

    return title


def classify_seniority_tier(clean_title_str: str) -> Tuple[str, int, str]:
    """
    Evaluates seniority tier from highest to lowest precedence:
    Returns (seniority_level, seniority_score, legacy_seniority).
    """
    t = clean_title_str.lower()

    # 1. VP & C-Level Executives
    if re.search(r"\b(?:vp|vice president|svp|evp|avp|chief|cpo|chro|head of|global head|practice leader|managing partner|co-founder|founder|managing director)\b", t):
        return "VP_EXECUTIVE", 6, "Executive"

    # 2. Directors
    if re.search(r"\b(?:director|sr\.?\s*director|senior director|associate director|group director)\b", t):
        return "DIRECTOR", 5, "Executive"

    # 3. Lead / Staff / Principal / Manager / Founding
    if re.search(r"\b(?:lead|team lead|staff|principal|manager|practice lead|recruiting lead|sourcing lead|talent manager|ta manager|supervisor|founding)\b", t):
        return "LEAD_STAFF", 4, "Lead"

    # 4. Senior
    if re.search(r"\b(?:senior|sr\b|sr\.|advanced|recruiter\s*iii|talent partner\s*iii|specialist\s*iii)\b", t):
        return "SENIOR", 3, "Senior"

    # 5. Entry-Level / Early Career / Campus
    if re.search(r"\b(?:junior|jr\b|jr\.|associate|intern|internship|trainee|apprentice|campus|university|college|early career|emerging talent|recruiting coordinator|talent coordinator|sdr|recruiting assistant|sourcer\s*i|recruiter\s*i)\b", t):
        return "ENTRY", 1, "Campus"

    # 6. Default: Mid-Level Specialist
    return "MID", 2, "Specialist"


def classify_domain_specialization(text: str) -> Tuple[str, str]:
    """
    Classifies domain specialization:
    Returns (domain_enum, domain_display_label).
    """
    t = text.lower()

    # 1. Executive Search & Leadership Practice
    if re.search(r"\b(?:executive search|leadership recruiting|leadership hiring|executive recruiter|retained search|c-level|board search|headhunter|executive talent|executive placement)\b", t):
        return "EXECUTIVE_SEARCH", SPECIALIZATION_LABELS["EXECUTIVE_SEARCH"]

    # 2. Technical & Engineering
    if re.search(r"\b(?:tech|technical|it\b|information technology|software|engineering|engineer|developer|ai\b|ml\b|artificial intelligence|machine learning|data science|data engineer|cloud|devops|cybersecurity|cyber|systems|hardware|firmware|infrastructure|quant|full stack|frontend|backend)\b", t):
        return "TECHNICAL", SPECIALIZATION_LABELS["TECHNICAL"]

    # 3. Go-To-Market, Sales & Commercial
    if re.search(r"\b(?:gtm|go-to-market|sales|account executive|business development|commercial|marketing|revenue|revops|customer success|growth|account manager)\b", t):
        return "GTM_SALES", SPECIALIZATION_LABELS["GTM_SALES"]

    # 4. Healthcare, Clinical & Life Sciences
    if re.search(r"\b(?:health|healthcare|clinical|nurse|nursing|medical|pharma|pharmaceutical|hospital|physician|allied health|biotech|therapeutics)\b", t):
        return "HEALTHCARE", SPECIALIZATION_LABELS["HEALTHCARE"]

    # 5. Finance, Accounting & Legal
    if re.search(r"\b(?:finance|financial|accounting|accountant|cpa|audit|banking|legal|compliance|risk|tax|investment|capital markets)\b", t):
        return "FINANCE_LEGAL", SPECIALIZATION_LABELS["FINANCE_LEGAL"]

    # 6. Talent & People Operations (Default for recruitment domain)
    return "OPERATIONS_GENERAL", SPECIALIZATION_LABELS["OPERATIONS_GENERAL"]


def classify_role_family(clean_title_str: str, seniority_level: str) -> str:
    """Classifies role family into RECRUITER, SOURCER, TALENT_OPS, HR_PEOPLE, or EXECUTIVE."""
    t = clean_title_str.lower()

    if seniority_level in ("DIRECTOR", "VP_EXECUTIVE"):
        return "EXECUTIVE"

    if re.search(r"\b(?:sourcer|sourcing|talent research|talent scout)\b", t):
        return "SOURCER"

    if re.search(r"\b(?:coordinator|operations|ops|enablement|systems|program manager|scheduling)\b", t):
        return "TALENT_OPS"

    if re.search(r"\b(?:hr|human resources|people ops|people partner|hrbp|people operations|culture)\b", t):
        return "HR_PEOPLE"

    return "RECRUITER"


def synthesize_canonical_title(
    clean_title_str: str,
    seniority_level: str,
    domain_enum: str,
    role_family: str,
) -> str:
    """
    Synthesizes a standardized canonical title from semantic components.
    """
    if not clean_title_str:
        return "Recruiter"

    t = clean_title_str.lower()

    # Retain well-formed executive titles with standard casing
    if "head of" in t:
        if "people" in t:
            return "Head of People"
        elif "technical" in t or domain_enum == "TECHNICAL":
            return "Head of Technical Recruiting"
        elif "talent" in t:
            return "Head of Talent"
        elif "recruiting" in t:
            return "Head of Recruiting"
        return clean_title_str.title()

    if "chief people officer" in t or "cpo" in t.split():
        return "Chief People Officer"

    if "chief talent officer" in t:
        return "Chief Talent Officer"

    if "vp" in t or "vice president" in t:
        if "talent acquisition" in t or "ta" in t.split():
            return "VP of Talent Acquisition"
        elif "talent" in t:
            return "VP of Talent"
        elif "people" in t:
            return "VP of People"
        return "VP of Talent"

    if "director" in t:
        prefix = "Senior " if ("sr" in t or "senior" in t) else ""
        if domain_enum == "TECHNICAL" or "technical" in t:
            return f"{prefix}Director of Technical Recruiting"
        elif "talent acquisition" in t or "ta" in t.split():
            return f"{prefix}Director of Talent Acquisition"
        elif "talent" in t:
            return f"{prefix}Director of Talent"
        elif "recruiting" in t:
            return f"{prefix}Director of Recruiting"
        elif "people" in t:
            return f"{prefix}Director of People"
        return f"{prefix}Director of Talent"

    domain_adj = ""
    if domain_enum == "TECHNICAL":
        domain_adj = "Technical "
    elif domain_enum == "EXECUTIVE_SEARCH":
        domain_adj = "Executive "
    elif domain_enum == "HEALTHCARE":
        domain_adj = "Healthcare "
    elif domain_enum == "FINANCE_LEGAL":
        domain_adj = "Finance "

    if "campus" in t:
        return f"{domain_adj}Campus Recruiter".strip()
    if "university" in t:
        return f"{domain_adj}University Recruiter".strip()
    if "founding" in t:
        return f"Founding {domain_adj}Recruiter".strip()
    if "people operations" in t or "people ops" in t:
        if "lead" in t or "manager" in t:
            return "People Operations Manager"
        return "People Operations Specialist"

    prefix_map = {
        "ENTRY": "Associate ",
        "MID": "",
        "SENIOR": "Senior ",
        "LEAD_STAFF": "Lead " if "manager" not in t and "staff" not in t and "principal" not in t else "",
    }
    if "staff" in t:
        prefix = "Staff "
    elif "principal" in t:
        prefix = "Principal "
    elif "manager" in t:
        prefix = "Lead " if "lead" in t else ""
    else:
        prefix = prefix_map.get(seniority_level, "")

    if role_family == "SOURCER":
        noun = "Sourcer"
    elif role_family == "TALENT_OPS":
        noun = "Talent Operations Specialist" if "coordinator" not in t else "Recruiting Coordinator"
    elif role_family == "HR_PEOPLE":
        noun = "People Operations Specialist" if "partner" not in t else "People Partner"
    else:
        if "manager" in t:
            noun = "Recruiting Manager"
        elif "partner" in t and "talent" in t:
            noun = "Talent Partner"
        elif "talent acquisition specialist" in t:
            noun = "Talent Acquisition Specialist"
        else:
            noun = "Recruiter"

    base = f"{domain_adj}{noun}".strip()
    if prefix:
        if base.lower().startswith(prefix.lower().strip()):
            candidate = base
        else:
            candidate = f"{prefix}{base}"
    else:
        candidate = base

    return candidate.strip().title() if candidate else "Recruiter"


def classify_title(raw_title: Optional[str]) -> Dict[str, Any]:
    """
    Main Classification Entry Point.
    Takes a raw title string and returns a complete semantic classification dictionary.
    """
    clean = strip_title_noise(raw_title)
    if not clean:
        clean = "Recruiter"

    # Evaluate domain specialization using both clean and full raw context
    combined_context = f"{raw_title or ''} {clean}"
    domain_enum, domain_label = classify_domain_specialization(combined_context)

    seniority_level, seniority_score, legacy_seniority = classify_seniority_tier(clean)
    role_family = classify_role_family(clean, seniority_level)
    canonical = synthesize_canonical_title(clean, seniority_level, domain_enum, role_family)

    is_people_mgr = bool(
        seniority_level in ("DIRECTOR", "VP_EXECUTIVE")
        or "manager" in clean.lower()
        or "lead" in clean.lower()
        or "head" in clean.lower()
    )

    return {
        "raw_title": raw_title or "",
        "cleaned_title": clean,
        "canonical_title": canonical,
        "seniority_level": seniority_level,
        "seniority_score": seniority_score,
        "legacy_seniority": legacy_seniority,
        "domain_specialization": domain_enum,
        "specialization_label": domain_label,
        "role_family": role_family,
        "is_people_manager": is_people_mgr,
        "confidence": 0.95 if raw_title else 0.50,
    }


def normalize_seniority_query_param(val: Optional[str]) -> Optional[str]:
    """
    Translates input query parameter into standardized legacy or granular value
    for search filtering.
    """
    if not val or not isinstance(val, str):
        return None
    cleaned = val.strip().lower().replace(" ", "_").replace("-", "_")
    return LEGACY_TO_SENIORITY_MAP.get(cleaned, val.strip())
