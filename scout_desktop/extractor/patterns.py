"""
extractor/patterns.py — Semantic Validation & Extraction Regex Engine

Translates and enhances validated extraction algorithms from the TalentScout core.
Includes strict location validation, title/company separation, degree markers,
and school detection.
"""

import re
from typing import Optional, Tuple, List

# Rejection keywords for locations (prevents "Power Engineering" distractor bug and educational institute overlap)
LOCATION_REJECT_TERMS = re.compile(
    r"\b(?:engineer|engineering|developer|recruiter|recruiting|talent|manager|"
    r"consultant|analyst|specialist|officer|director|lead|head|vp|president|"
    r"designer|scientist|marketing|sales|architect|intern|assistant|advisor|"
    r"technician|contract|full-time|part-time|hybrid|corp|corporation|inc|"
    r"llc|ltd|gmbh|technologies|technology|tech|solutions|services|group|holdings|"
    r"university|college|institute|school|academy|polytechnic|alumni|student|"
    r"bachelor|master|doctor|phd|degree)\b",
    re.IGNORECASE,
)

# Comprehensive geographic indicators (US States, Countries, Major Global Tech Metro Hubs)
# Note: Two-letter state abbreviations are handled via uppercase or comma-syntax to prevent "in", "or", "me" false positives.
GEO_INDICATORS = re.compile(
    r"\b(?:area|greater|city|county|region|metro|metropolitan|district|remote|"
    r"united states|united kingdom|usa|uk|canada|india|australia|germany|france|"
    r"netherlands|singapore|brazil|spain|italy|ireland|switzerland|sweden|japan|"
    r"uae|dubai|mexico|poland|philippines|alabama|alaska|arizona|arkansas|california|"
    r"colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|"
    r"iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|"
    r"new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|"
    r"south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|"
    r"west virginia|wisconsin|wyoming|england|scotland|wales|london|boston|chicago|seattle|"
    r"austin|san francisco|sf bay|los angeles|atlanta|dallas|houston|denver|phoenix|"
    r"philadelphia|san diego|miami|portland|toronto|vancouver|berlin|paris|amsterdam|"
    r"tokyo|sydney|melbourne|bangalore|bengaluru|mumbai|hyderabad|pune|chennai|delhi|"
    r"noida|gurgaon|raleigh|durham|chapel hill|san jose|salt lake city|dallas-fort worth)\b|"
    r"(?:,\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b)",
    re.IGNORECASE,
)

UI_ACTIONS = re.compile(
    r"^(?:message|connect|follow|more|save|share|view|endorse|view profile|"
    r"open to work|hiring|verified|contact info)$",
    re.IGNORECASE,
)

PRONOUNS = re.compile(
    r"^(?:he/him|she/her|they/them|she/they|he/they)$",
    re.IGNORECASE,
)

METRICS = re.compile(
    r"\b(?:followers?|connections?|mutual|following|network)\b",
    re.IGNORECASE,
)

SCHOOL_KEYWORDS = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic|penn state|"
    r"harvard|stanford|mit|oxford|cambridge|alabama|berkeley|ucla|nyu|purdue|"
    r"columbia|cornell|umass|massachusetts|bachelor|master|mba|ph\.?d|b\.?s\b|b\.?a\b|"
    r"iit\b|bits\b|caltech|insead|notre dame|virginia tech|uiuc\b|georgia tech|"
    r"usc\b|carnegie mellon|cmu\b|waterloo|imperial college|lse\b|london business school|"
    r"eth zurich|tsinghua|wharton|dartmouth|amherst|williams|yale|princeton|duke|"
    r"northwestern|vanderbilt|rice|emory|georgetown|johns hopkins|uc berkeley|"
    r"university of [a-zA-Z\s]+|[a-zA-Z\s]+ university|[a-zA-Z\s]+ institute of technology)\b",
    re.IGNORECASE,
)

DEGREE_KEYWORDS = re.compile(
    r"\b(?:bachelor(?:'s)?|master(?:'s)?|doctor(?:ate)?|ph\.?d|dphil|b\.?s\b|b\.?a\b|b\.?sc\b|b\.?eng\b|"
    r"b\.?tech\b|b\.?e\b|m\.?s\b|m\.?a\b|m\.?sc\b|m\.?eng\b|m\.?tech\b|m\.?b\.?a\b|mba\b|"
    r"associate(?:'s)?|diploma|certificate|juris doctor|j\.?d\b|m\.?d\b)\b",
    re.IGNORECASE,
)

TITLE_KEYWORDS = re.compile(
    r"\b(?:director|manager|recruiter|recruiting|sourcer|engineer|engineering|"
    r"developer|specialist|consultant|analyst|officer|lead|head|vp|president|"
    r"designer|scientist|architect|advisor|partner|technician|intern|assistant|"
    r"chairman|chairperson|chair|executive|founder|co-founder|chief|ceo|cto|cfo|coo|cro|cmo|"
    r"principal|fellow|associate|administrator|coordinator|strategist|leader|counsel)\b",
    re.IGNORECASE,
)


def is_plausible_school(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents a legitimate educational institution."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 90:
        return False
    if is_noise_text(t) or is_valid_location(t):
        return False
    return bool(SCHOOL_KEYWORDS.search(t))


def is_plausible_degree(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents an academic degree or field of study."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 100:
        return False
    return bool(DEGREE_KEYWORDS.search(t))


def is_plausible_title(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents a professional job title."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 75:
        return False
    return bool(TITLE_KEYWORDS.search(t))


def clean_location_text(text: Optional[str]) -> Optional[str]:
    """Cleans punctuation, bullets, and contact info triggers from location strings."""
    if not text:
        return None
    cleaned = re.sub(r"\bcontact\s*info\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$", "", cleaned)
    cleaned = re.sub(r"^[\s\-_,·•|]+|[\s\-_,·•|]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else None


def is_valid_location(text: Optional[str]) -> bool:
    """
    Strict Semantic Location Validation.
    Rejects titles, industries, company suffixes, credentials, pronouns, and metrics.
    Requires genuine geographic indicators or standard city, state/country syntax.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 80:
        return False

    # Reject pronouns & metrics
    if PRONOUNS.match(t) or METRICS.search(t):
        return False

    # Reject connection degrees (1st, 2nd, 3rd)
    if re.match(r"^[·•\s]*\d*(?:st|nd|rd|th)?(?:\s*degree)?$", t, re.IGNORECASE):
        return False

    # Reject UI actions
    if UI_ACTIONS.match(t):
        return False

    # Reject pure numbers or dates
    if re.match(r"^\d+$", t) or re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b", t, re.IGNORECASE):
        return False

    # Reject job roles, disciplines, industries, and company suffix words
    if LOCATION_REJECT_TERMS.search(t):
        return False

    # Must match genuine geographic keyword
    if GEO_INDICATORS.search(t):
        return True

    # Standard "City, State/Country" with 2-letter state code or standard comma separation
    if re.match(r"^[A-Z][a-zA-Z\s.-]+,\s*[A-Z]{2}$", t):
        return True
    if re.match(r"^[A-Z][a-zA-Z\s.-]+,\s*[A-Z][a-zA-Z\s.-]+,\s*[A-Z][a-zA-Z\s.-]+$", t):
        return True

    return False


def extract_connection_degree(text: Optional[str]) -> Optional[str]:
    """Extracts connection degree (1st, 2nd, 3rd, 3rd+)."""
    if not text:
        return None
    m = re.search(r"\b(1st|2nd|3rd(?:\+)?)(?!\w)", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def clean_title_and_company(headline: Optional[str], raw_company: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Decomposes headline into clean title and employer when connected by '@', 'at', '|'.
    Example: 'Senior Talent Partner @ Cyberdyne Systems | AI Engineering'
      -> Title: 'Senior Talent Partner', Company: 'Cyberdyne Systems'
    """
    if not headline:
        return None, raw_company

    title = headline.strip()
    company = raw_company

    # Split on ' @ ' or ' at ' (requiring whitespace around @ to ignore email addresses)
    if re.search(r"\s+@\s+", title):
        parts = re.split(r"\s+@\s+", title, maxsplit=1)
        title = parts[0].strip()
        comp_part = parts[1].split("|")[0].split("•")[0].strip()
        if comp_part and not company:
            company = comp_part
    elif re.search(r"\s+at\s+", title, re.IGNORECASE):
        parts = re.split(r"\s+at\s+", title, maxsplit=1, flags=re.IGNORECASE)
        title = parts[0].strip()
        comp_part = parts[1].split("|")[0].split("•")[0].strip()
        if comp_part and not company:
            company = comp_part

    # Clean separators from title
    title = re.split(r"\s*[|•·]\s*", title)[0].strip()

    if company:
        company = re.sub(r"^Current\s*company:\s*", "", company, flags=re.IGNORECASE)
        company = re.sub(r"\. Click to skip.*$", "", company, flags=re.IGNORECASE)
        company = re.sub(r"[·•|].*$", "", company).strip()

    return title or None, company or None


DATE_RANGE_PATTERN = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b.*\b(?:present|\d{4})\b",
    re.IGNORECASE,
)

WORKPLACE_TYPES = re.compile(
    r"\b(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site)\b",
    re.IGNORECASE,
)


def clean_company_name(comp: Optional[str]) -> Optional[str]:
    """Cleans employment type, bullets, and UI triggers from company strings."""
    if not comp:
        return None
    cleaned = comp.strip()
    cleaned = re.sub(r"^Current\s*company:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\. Click to skip.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\s*[·•|]\s*(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site).*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"[·•|].*$", "", cleaned).strip()
    return cleaned if len(cleaned) >= 2 else None


def is_valid_company_name(text: Optional[str]) -> bool:
    """Validates whether a candidate string is a plausible company name."""
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 60:
        return False
    # Reject window titles and platform URLs
    if " | linkedin" in t.lower() or " - linkedin" in t.lower() or t.lower().endswith("linkedin") or "linkedin.com" in t.lower():
        return False
    # Civic, government, institutional organizations that may contain geographic names (e.g. City and County of San Francisco, Port of Oakland)
    is_civic_or_org = bool(re.search(
        r"\b(?:city\s+and\s+county|city\s+of|county\s+of|state\s+of|port\s+of|department\s+of|"
        r"department|commission|authority|administration|district|foundation|institute|hospital|"
        r"health\s+system|schools?)\b",
        t,
        re.IGNORECASE,
    ))
    if not is_civic_or_org and is_valid_location(t):
        return False
    if is_noise_text(t):
        return False
    if DATE_RANGE_PATTERN.search(t):
        return False
    # Reject social proof, connections, and activity lines
    if re.search(
        r"\b(?:followed by|mutual connection|connections|followers|people you may know|"
        r"talks about|activity|show all|see all|shared by|reposts|profile views|"
        r"connect|message|view full profile|more profiles)\b",
        t,
        re.IGNORECASE,
    ):
        return False
    # Reject lines that look like sentences or have verbs like "looking for", "helping"
    if re.search(r"\b(?:looking for|helping|building|passionate about|specializing in)\b", t, re.IGNORECASE):
        return False
    # Pure job titles are not company names unless they contain explicit corporate/org identifiers
    has_comp_suffix = bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|group|partners|holdings|labs|studio|ventures|consulting|agency|capital|systems)\b", t, re.IGNORECASE))
    if not has_comp_suffix and is_plausible_title(t):
        return False
    return True


def is_valid_skill(text: Optional[str]) -> bool:
    """Validates whether a candidate string represents a legitimate professional skill."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 50:
        return False
    if is_noise_text(t) or is_valid_location(t):
        return False
    # Reject UI noise in skills sections
    if re.search(
        r"\b(?:show all|see all|endorse|endorsed|passed skill|assessment|quiz|recommendation|"
        r"view|learn more|click to|add skill|skills\b|top skills)\b",
        t,
        re.IGNORECASE,
    ):
        return False
    # Reject pure numbers or dates
    if re.match(r"^\d+$", t) or DATE_RANGE_PATTERN.search(t):
        return False
    return True


def is_noise_text(text: Optional[str]) -> bool:
    """Detects boilerplate navigation, UI buttons, social proof, and cookie banners."""
    if not text:
        return True
    t = text.strip().lower()
    if len(t) < 2:
        return True
    noise_phrases = [
        "see all", "view full profile", "sign in to view", "join now",
        "accept cookies", "privacy policy", "terms of service", "skip to main content",
        "keyboard shortcuts", "all rights reserved", "contact info",
        "followed by", "mutual connection", "mutual connections",
        "people also viewed", "more profiles for", "show all", "show more",
        "connections", "followers", "activity", "highlights", "interests",
        "send message", "more actions", "pending", "open to",
    ]
    return any(p in t for p in noise_phrases)


def is_valid_person_name(text: Optional[str]) -> bool:
    """
    Validates if a text string is a plausible candidate person name.
    Rejects connection degrees ('· 1st', '2nd'), company names, UI actions, locations, headings.
    Requires at least two capitalized alphabetic name parts.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    # Strip pronouns first before validation
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    if len(t) < 3 or len(t) > 50:
        return False
    if is_noise_text(t) or is_valid_location(t) or extract_connection_degree(t):
        return False
    if UI_ACTIONS.match(t) or re.search(r"^[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]", t):
        return False

    if any(c.isdigit() for c in t):
        return False

    words = t.split()
    # Filter for alphabetic words (allowing hyphens or apostrophes in names e.g. O'Connor, Anne-Marie)
    clean_words = [re.sub(r"[^a-zA-Z\'-]", "", w) for w in words]
    clean_words = [w for w in clean_words if w and any(c.isalpha() for c in w)]
    if len(clean_words) < 2 or len(clean_words) > 4:
        return False
    # Avoid single letter abbreviations as full first name (e.g. 'M Inbox' from mail icons)
    if any(len(w) < 2 for w in clean_words):
        return False
    # Every word must start with an uppercase letter
    if not all(w[0].isupper() for w in clean_words):
        return False
    # Check for non-name title/role/section/system words
    lower_words = [w.lower() for w in clean_words]
    blacklisted = {
        "experience", "education", "skills", "about", "activity", "interests",
        "recommendations", "people", "results", "search", "connections", "followers",
        "director", "recruiter", "manager", "engineer", "sourcer", "specialist",
        "consultant", "analyst", "current", "previous", "view", "contact",
        "university", "college", "institute", "school", "company", "group", "team",
        "inbox", "mail", "gmail", "outlook", "gemini", "chatgpt", "claude", "copilot",
        "chat", "assistant", "jobs", "apply", "feed", "home", "notifications",
        "network", "windows", "tab", "chrome", "firefox", "edge", "safari",
        "post", "posts", "quick", "easy", "prompt", "top", "united", "states",
        "history", "conversation", "conversations", "profile", "profiles",
        "message", "messages", "filter", "filters", "dialog", "session", "menu",
    }
    if any(w in blacklisted for w in lower_words):
        return False
    return True


EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
PHONE_REGEX = re.compile(r"(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}")


def clean_person_name(text: Optional[str]) -> Optional[str]:
    """
    Strips degree badges (• 2nd, · 1st), pronouns, bullets, and validates clean candidate name.
    Example: 'Mariam Nguyen • 2nd' -> 'Mariam Nguyen'
    """
    if not text:
        return None
    t = text.strip()
    # Strip degree suffixes: • 2nd, · 1st, 3rd, etc.
    t = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd(?:\+)?).*$", "", t, flags=re.IGNORECASE).strip()
    # Strip pronouns in parens/brackets/free: (she/her), [she/her], (he/him), etc.
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    # Strip trailing badges / dots / icons
    t = re.sub(r"[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$", "", t).strip()
    return t if is_valid_person_name(t) else None


