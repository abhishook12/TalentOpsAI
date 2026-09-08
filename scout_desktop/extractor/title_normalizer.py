"""
scout_desktop/extractor/title_normalizer.py — Client-Side Title Normalizer & Seniority Engine.

Identical classification logic as backend/app/utils/title_normalizer.py.
Provides instant, client-side semantic title canonicalization and seniority classification
for candidate profile extraction.
"""

import re
from typing import Dict, Any, Optional, Tuple

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

BUZZWORD_STRIP_RE = re.compile(
    r"\b(?:ninja|rockstar|guru|wizard|champion|hero|maven|jedi|enthusiast|evangelist|magician|superhero|overlord)\b",
    re.IGNORECASE,
)

CREDENTIALS_STRIP_RE = re.compile(
    r"(?:,\s*|\s+[-–|]\s*)(?:MBA|SPHR|PHR|SHRM-CP|SHRM-SCP|PMP|PhD|CPA|MS|BS|BA|JD|MD|CIPD)\b",
    re.IGNORECASE,
)

STATUS_TAG_STRIP_RE = re.compile(
    r"[\(\[\{](?:we'?re\s*(?:actively\s*)?hiring|actively\s*hiring|hiring|open\s*to\s*work|open\s*to\s*new\s*opportunities|seeking\s*opportunities|looking\s*for\s*roles|ex-[\w\s]+)[\)\]\}]|#opentowork|#hiring",
    re.IGNORECASE,
)

EMOJI_CLEAN_RE = re.compile(r"[^\w\s\.\,\-\/\&\'\(\)]")


def strip_title_noise(raw_title: Optional[str]) -> str:
    """Removes emojis, UI buzzwords, credentials, status tags, and employer company suffixes."""
    if not raw_title or not isinstance(raw_title, str):
        return ""

    title = raw_title.strip()
    title = STATUS_TAG_STRIP_RE.sub("", title)
    title = CREDENTIALS_STRIP_RE.sub("", title)

    at_match = re.search(r"\s+(?:@|at)\s+[\w\s\.\,\&\'-]+$", title, re.IGNORECASE)
    if at_match:
        title = title[:at_match.start()].strip()

    if " | " in title or " – " in title:
        parts = re.split(r"\s+[\|–]\s+", title)
        filtered = [p for p in parts if not re.search(r"\b(?:ex-|we\s*build|hiring|passion|helping)\b", p, re.IGNORECASE)]
        title = " | ".join(filtered) if filtered else parts[0]

    title = BUZZWORD_STRIP_RE.sub("", title)
    title = EMOJI_CLEAN_RE.sub(" ", title)
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"[,\|\-–\.\s]+$", "", title).strip()
    return title


def classify_seniority_tier(clean_title_str: str) -> Tuple[str, int, str]:
    t = clean_title_str.lower()
    if re.search(r"\b(?:vp|vice president|svp|evp|avp|chief|cpo|chro|head of|global head|practice leader|managing partner|co-founder|founder|managing director)\b", t):
        return "VP_EXECUTIVE", 6, "Executive"
    if re.search(r"\b(?:director|sr\.?\s*director|senior director|associate director|group director)\b", t):
        return "DIRECTOR", 5, "Executive"
    if re.search(r"\b(?:lead|team lead|staff|principal|manager|practice lead|recruiting lead|sourcing lead|talent manager|ta manager|supervisor|founding)\b", t):
        return "LEAD_STAFF", 4, "Lead"
    if re.search(r"\b(?:senior|sr\b|sr\.|advanced|recruiter\s*iii|talent partner\s*iii|specialist\s*iii)\b", t):
        return "SENIOR", 3, "Senior"
    if re.search(r"\b(?:junior|jr\b|jr\.|associate|intern|internship|trainee|apprentice|campus|university|college|early career|emerging talent|recruiting coordinator|talent coordinator|sdr|recruiting assistant|sourcer\s*i|recruiter\s*i)\b", t):
        return "ENTRY", 1, "Campus"
    return "MID", 2, "Specialist"


def classify_domain_specialization(text: str) -> Tuple[str, str]:
    t = text.lower()
    if re.search(r"\b(?:executive search|leadership recruiting|leadership hiring|executive recruiter|retained search|c-level|board search|headhunter|executive talent|executive placement)\b", t):
        return "EXECUTIVE_SEARCH", SPECIALIZATION_LABELS["EXECUTIVE_SEARCH"]
    if re.search(r"\b(?:tech|technical|it\b|information technology|software|engineering|engineer|developer|ai\b|ml\b|artificial intelligence|machine learning|data science|data engineer|cloud|devops|cybersecurity|cyber|systems|hardware|firmware|infrastructure|quant|full stack|frontend|backend)\b", t):
        return "TECHNICAL", SPECIALIZATION_LABELS["TECHNICAL"]
    if re.search(r"\b(?:gtm|go-to-market|sales|account executive|business development|commercial|marketing|revenue|revops|customer success|growth|account manager)\b", t):
        return "GTM_SALES", SPECIALIZATION_LABELS["GTM_SALES"]
    if re.search(r"\b(?:health|healthcare|clinical|nurse|nursing|medical|pharma|pharmaceutical|hospital|physician|allied health|biotech|therapeutics)\b", t):
        return "HEALTHCARE", SPECIALIZATION_LABELS["HEALTHCARE"]
    if re.search(r"\b(?:finance|financial|accounting|accountant|cpa|audit|banking|legal|compliance|risk|tax|investment|capital markets)\b", t):
        return "FINANCE_LEGAL", SPECIALIZATION_LABELS["FINANCE_LEGAL"]
    return "OPERATIONS_GENERAL", SPECIALIZATION_LABELS["OPERATIONS_GENERAL"]


def classify_role_family(clean_title_str: str, seniority_level: str) -> str:
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
    if not clean_title_str:
        return "Recruiter"

    t = clean_title_str.lower()

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

    if "chief" in t or any(k in t.split() for k in ["cpo", "cio", "cto", "ceo", "coo", "cfo"]):
        if "information" in t or "cio" in t.split():
            return "Chief Information Officer"
        elif "technology" in t or "cto" in t.split():
            return "Chief Technology Officer"
        elif "executive" in t or "ceo" in t.split():
            return "Chief Executive Officer"
        elif "operating" in t or "coo" in t.split():
            return "Chief Operating Officer"
        elif "financial" in t or "cfo" in t.split():
            return "Chief Financial Officer"
        elif "people" in t or "cpo" in t.split():
            return "Chief People Officer"
        elif "talent" in t:
            return "Chief Talent Officer"
        return clean_title_str.title()

    if "vp" in t or "vice president" in t:
        if "engineering" in t or "eng" in t.split():
            return "VP of Engineering"
        elif "product" in t:
            return "VP of Product"
        elif "sales" in t:
            return "VP of Sales"
        elif "marketing" in t:
            return "VP of Marketing"
        elif "finance" in t:
            return "VP of Finance"
        elif "operations" in t or "ops" in t:
            return "VP of Operations"
        elif "talent acquisition" in t or "ta" in t.split():
            return "VP of Talent Acquisition"
        elif "talent" in t:
            return "VP of Talent"
        elif "people" in t:
            return "VP of People"
        return "VP of " + clean_title_str.replace("Vice President of", "").replace("Vice President", "").replace("VP of", "").replace("VP", "").strip().title()

    if "director" in t:
        prefix = "Senior " if ("sr" in t or "senior" in t) else ""
        if "engineering" in t:
            return f"{prefix}Director of Engineering"
        elif "product" in t:
            return f"{prefix}Director of Product"
        elif "sales" in t:
            return f"{prefix}Director of Sales"
        elif "marketing" in t:
            return f"{prefix}Director of Marketing"
        elif "finance" in t:
            return f"{prefix}Director of Finance"
        elif "operations" in t:
            return f"{prefix}Director of Operations"
        elif "talent acquisition" in t or "ta" in t.split():
            return f"{prefix}Director of Talent Acquisition"
        elif "talent" in t:
            return f"{prefix}Director of Talent"
        elif "recruiting" in t:
            return f"{prefix}Director of Recruiting"
        elif "people" in t:
            return f"{prefix}Director of People"
        elif domain_enum == "TECHNICAL" or "technical" in t:
            return f"{prefix}Technical Director"
        return f"{prefix}{clean_title_str.title()}"

    # General technical / engineering / product candidate titles
    if not any(k in t for k in ["recruit", "talent", "sourc", "staffing", "ta "]):
        if any(k in t for k in ["engineer", "architect", "developer", "scientist", "analyst", "designer", "product manager", "program manager"]):
            return clean_title_str.title()

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
    clean = strip_title_noise(raw_title)
    if not clean:
        clean = "Recruiter"

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
