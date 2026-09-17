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
    r"noida|gurgaon|raleigh|durham|chapel hill|san jose|salt lake city|dallas-fort worth)\b",
    re.IGNORECASE,
)

# Strict uppercase 2-letter US state code requiring preceding city name of >= 2 characters
US_STATE_POSTAL_REGEX = re.compile(
    r"^[A-Za-z\s.-]{2,},\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)$"
)

UI_ACTIONS = re.compile(
    r"^(?:message|connect|follow|more|save|share|view|endorse|view profile|"
    r"open to work|hiring|verified|contact info|"
    r"export|suggest update|reveal|contact profile|contact details|"
    r"contact management|similar companies|overview|employees|premium features|"
    r"scheduled emails|web visits|crm integrations|zoominfo lite|zoominfo|homepage|quick search|"
    r"home|feed|jobs|messaging|notifications|my network|business|learning|work|sent items|address book)$",
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
    r"principal|fellow|associate|administrator|coordinator|strategist|leader|counsel|"
    r"supervisor|expert|educator|instructor|teacher|professor|trainer|coach|"
    r"writer|editor|producer|artist|marketer|accountant|auditor|lawyer|attorney|"
    r"physician|doctor|nurse|therapist|pharmacist|practitioner|operator|representative|"
    r"advocate|agent|buyer|trader|underwriter|broker|investor|statistician|economist|researcher|scholar)\b",
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
    """Cleans punctuation, bullets, timestamps, and contact info triggers from location strings."""
    if not text:
        return None
    cleaned = re.sub(r"\bcontact\s*info\b", "", text, flags=re.IGNORECASE)
    # Strip relative timestamps e.g. "4 minutes ago 0", "2 hours ago", "3d ago"
    cleaned = re.sub(r"\b\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*(?:m|min|h|hr|d|w|mo|y)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\d+$", "", cleaned)
    cleaned = re.sub(r"[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$", "", cleaned)
    # Strip trailing hyphen/dash fragments e.g. " - sud", " - ntu"
    cleaned = re.sub(r"\s*[-–—]\s*[a-zA-Z]{1,4}$", "", cleaned)
    # Strip single-letter prefix before comma e.g. "D, "
    cleaned = re.sub(r"^[a-zA-Z],\s*", "", cleaned)
    cleaned = re.sub(r"^[\s\-_,·•|:]+|[\s\-_,·•|:]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else None


def is_valid_location(text: Optional[str]) -> bool:
    """
    Strict Semantic Location Validation.
    Rejects titles, industries, company suffixes, credentials, pronouns, metrics,
    and corrupted OCR fragments (e.g. 'D,id - sud', 'San ntu').
    Requires genuine geographic indicators or standard city, state/country syntax.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 80:
        return False

    # Reject OCR artifacts with internal comma without whitespace (e.g. "D,id", "San,Jose")
    if re.search(r"[a-zA-Z],[a-zA-Z]", t):
        return False

    # Reject single-letter tokens immediately before a comma (e.g. "D, id", "A, NY")
    if re.search(r"\b[a-zA-Z],\s*", t):
        return False

    # Reject dangling hyphens or fragments (e.g. "- sud", "sud -")
    if re.search(r"[-–—]\s*[a-zA-Z]{1,4}\b", t) or t.startswith("-") or t.endswith("-"):
        return False

    # Reject strings with non-standard punctuation chaos or replacement chars
    if any(c in t for c in [";", ":", "?", "!", "~", "*", "=", "<", ">", "%", "\ufffd"]):
        return False

    # Words in location must be plausible words (not all short fragments)
    tokens = [tok for tok in re.split(r"[\s,.-]+", t) if tok]
    if not tokens or all(len(tok) < 3 for tok in tokens):
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

    # Strict US State Postal abbreviation (e.g. "San Francisco, CA", "Boise, ID")
    if US_STATE_POSTAL_REGEX.match(t):
        return True

    # Must match genuine geographic keyword
    if GEO_INDICATORS.search(t):
        return True

    # Standard "City, State/Country" with 2-letter state code or standard comma separation
    if re.match(r"^[A-Z][a-zA-Z\s.-]+,\s*[A-Z]{2}$", t):
        return True
    if re.match(r"^[A-Z][a-zA-Z\s.-]+,\s*[A-Z][a-zA-Z\s.-]+(?:,\s*[A-Z][a-zA-Z\s.-]+)?$", t):
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

    # Split on ' @ ' or ' at ' (supporting leading '@ ' when headline is wrapped across lines)
    if re.search(r"(?:^|\s+)@\s+", title):
        parts = re.split(r"(?:^|\s+)@\s+", title, maxsplit=1)
        if not parts[0].strip() and len(parts) > 1:
            comp_part = parts[1].split("|")[0].split("•")[0].strip()
            if comp_part and not company:
                company = comp_part
            title = None
        else:
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
    if title:
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
    """Cleans employment type, bullets, contact info, and UI triggers from company strings."""
    if not comp:
        return None
    cleaned = comp.strip()
    # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] ", "(1) "
    cleaned = re.sub(r"^(?:[\(\[]?\d+\+?[\)\]]?\s*[|•·–—\-:]?\s*)+", "", cleaned).strip()
    cleaned = re.sub(r"^Current\s*company:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\. Click to skip.*$", "", cleaned, flags=re.IGNORECASE)
    # Strip contact info and UI noise triggers
    cleaned = re.sub(r"\b(?:contact\s*info|contact|connections|followers)\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"\s*[·•|]\s*(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site).*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"[·•|].*$", "", cleaned).strip()
    cleaned = re.sub(r"^[\s\-_,·•|:]+|[\s\-_,·•|:]+$", "", cleaned).strip()
    return cleaned if len(cleaned) >= 2 else None


def is_valid_company_name(text: Optional[str]) -> bool:
    """Validates whether a candidate string is a plausible company name."""
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 60:
        return False

    t_lower = t.lower()

    # Reject window titles, platform URLs, and navigation/inbox patterns
    if " | linkedin" in t_lower or " - linkedin" in t_lower or t_lower.endswith("linkedin") or "linkedin.com" in t_lower:
        return False

    # Reject email/inbox, mailings, and chat/message titles
    if any(m in t_lower for m in ["inbox", "mailings", "domain search", "messaged you", "active window", "overview", "candidate card", "quick easy prompt"]):
        return False

    # Reject notification counters e.g. (121), (2), (54)
    if re.search(r"\(\d+\+?\)", t):
        return False

    # Reject truncated strings ending with ellipses e.g. "54 Ri Ht...", "abhish..."
    if t.endswith("...") or t.endswith("..") or re.search(r"\.{2,}", t):
        return False

    # Reject leading notification digits e.g. "355 M Inbox", "54 Ri"
    if re.match(r"^\d+\s+[A-Za-z0-9]\b", t):
        return False

    # Reject short words that are pronouns, prepositions, or OCR fragments (e.g. "My", "In", "At", "By", "To", "iHHI")
    if len(t) <= 2:
        return False
    if t_lower in {"my", "to", "in", "at", "by", "we", "he", "me", "us", "it", "or", "if", "on", "as", "an", "so", "no", "up", "do", "go", "is", "be"}:
        return False

    # Reject common filler words or pronouns as standalone company names
    if t_lower in {"any", "some", "every", "all", "none", "each", "both", "either", "neither", "other", "another"}:
        return False

    # Reject OCR artifacts with repeated letters or barcode-like patterns e.g. "iHHI", "lIllI", "|||"
    if re.match(r"^[iIl1|Hh]{3,}$", t):
        return False

    # Reject unicode replacement character
    if "\ufffd" in t or "\\ufffd" in t or "\uFFFD" in t:
        return False

    # Reject email addresses or web paths mistaken as companies
    if "@" in t or "http://" in t or "https://" in t or "www." in t or "/app/" in t_lower or "/chat/" in t_lower:
        return False

    # ===== Strict OCR Corruption & Mixed Casing Glitch Filter =====
    # Real company names do NOT have lowercase followed by multiple uppercase letters (e.g. "cotAMt")
    # Real company names do NOT end with a single uppercase letter after lowercase (e.g. "fiM")
    comp_tokens = t.split()
    for tok in comp_tokens:
        clean_tok = re.sub(r"[^a-zA-Z]", "", tok)
        if not clean_tok:
            continue
        # Lowercase followed by 2+ uppercase letters (e.g. "cotAMt", "teSTing")
        if re.search(r"[a-z]+[A-Z]{2,}", clean_tok):
            return False
        # 2+ lowercase letters followed by single uppercase at end (e.g. "fiM", "producT")
        if len(clean_tok) >= 3 and re.search(r"^[a-z]{2,}[A-Z]$", clean_tok):
            return False
        # Interior uppercase alternation chaos (e.g. "cOtAmT")
        if re.search(r"[a-z][A-Z][a-z][A-Z]", clean_tok):
            return False
        # Starts with lowercase then 2+ uppercase (e.g. "cOTamt")
        if re.search(r"^[a-z][A-Z]{2,}", clean_tok):
            return False

    # Reject if ALL tokens are short filler words or OCR fragments (e.g. "cotamt fim any")
    if all(tok.lower() in {"cotamt", "fim", "any", "the", "and", "or", "in", "of", "to", "a", "an", "is", "for"} for tok in comp_tokens):
        return False

    # Reject OCR misreadings of "Contact info" or LinkedIn UI text
    if any(phrase in t_lower for phrase in [
        "cotamt", "fim any", "cotamt fim", "contact info", "cotamt fim any",
        "contact details", "contact profile", "mutual connections",
        "see all connections", "people also viewed",
    ]):
        return False

    # ===== Chrome / Browser / System UI Noise Blocklist =====
    # These are UI elements that OCR frequently misreads as company names
    chrome_ui_noise = {
        "ask gemini", "gemini", "apps", "search", "more tools", "new tab",
        "bookmarks", "downloads", "history", "extensions", "settings",
        "reading list", "side panel", "tab groups", "chrome web store",
        "customize chrome", "incognito", "cast", "print", "find",
        "zoom", "translate", "passwords", "autofill", "privacy",
        "sync", "about chrome", "help", "exit", "quit",
        "admin settings", "find people", "more actions",
        # LinkedIn UI noise
        "rmt (you)", "(you)", "connect", "message", "follow",
        "linkedin premium", "linkedin recruiter", "try premium",
        "cotamt", "cotamt fim any", "cotamt fim", "fim any", "fim",
        "contact info", "contact details", "contact management",
        # System / taskbar noise
        "ultraviewer", "teamviewer", "anydesk", "task manager",
        "file explorer", "command prompt", "powershell", "terminal",
        # Chat & Collaboration noise
        "microsoft teams", "teams", "google chat", "slack", "new chat",
        "recent chats", "business intelligence", "busmess inteligence",
        "pinned messages", "chat files", "posts", "activity", "calendar",
        "channel notifications", "general", "recent", "chat",
        # Sourcing / OCR noise words and truncated fragments
        "ctv-", "ctv", "gmai", "ynai", "outbok", "dahyaa", "ryzir", "ryzirk",
        "azusasolutions", "azusasdutions", "azusasdgtions", "impresiviwalth",
        "tnnsowceiic", "oracbcontractors", "oraciecontractors", "epnec metrcvolitan",
        "houstadt", "caudting", "javiles", "supertsi", "stcu", "malik", "jain",
        "hdlstadt ca-aating", "hdlstadt", "paladininc",
        # Bogus UI & navigation noise
        "home", "feed", "jobright", "chatgpt", "turboscribe", "email id table",
        "ats", "at", "guided search", "guided search partners", "i'm locking",
        "homepage", "inbox", "messaging", "notifications", "my network", "jobs",
        "for business", "learning", "me", "sent items", "address book", "format text",
        "chelsie walsh", "kelly moran", "jeff thomas", "brenda geisler",
    }
    if t_lower in chrome_ui_noise:
        return False

    # Single-word companies under 4 characters are almost always OCR fragments unless on whitelist
    if len(comp_tokens) == 1 and len(t) < 4:
        valid_short_corps = {"ibm", "sap", "pwc", "hp", "ey", "bp", "ge", "att", "ups", "aws", "bnp", "dhl", "adp"}
        if t_lower not in valid_short_corps:
            return False

    # Reject strings starting or ending with special characters or trailing digits (OCR artifacts like "%iApps", "-5", "System;", "281-")
    if t[0] in "-–—_%#@!~`^&*()[]{}<>|\\;:\"'/?." or t[-1] in "-–—_%#@!~`^&*()[]{}<>|\\;:\"'/?.,":
        return False
    if t[-1].isdigit():
        return False
    if any(c in t for c in [";", ":", "?", "!", "~", "*", "=", "<", ">"]):
        return False
    # Reject strings containing phone numbers or area codes (e.g. "281-", "555-1234")
    if re.search(r"\b\d{3,}[-\s]?\b", t):
        return False
    # Reject strings containing individual professional job titles (e.g. "Cindy Davis Consultant")
    if re.search(r"\b(?:consultant|recruiter|sourcer|coordinator|advisor|specialist|manager|director|officer)\b", t, re.IGNORECASE):
        return False

    # Reject standalone department abbreviations or isolated 2-letter tokens
    if t_lower in {"it", "hr", "qa", "pr", "ai", "ml", "bi", "ui", "ux", "rd", "pm", "is"}:
        return False

    # Reject pure numeric or very short alphanumeric strings (like "-5", "IT", "aa")
    stripped_alpha = re.sub(r"[^a-zA-Z]", "", t)
    if len(stripped_alpha) < 2:
        return False

    # Reject system/desktop identifiers (e.g. "DESKTOP-GMM7KIN (130891427) UltraViewer")
    if re.match(r"^DESKTOP-", t, re.IGNORECASE):
        return False

    # Reject strings containing system/remote desktop identifiers
    if any(sw in t_lower for sw in ["ultraviewer", "teamviewer", "anydesk", "desktop-"]):
        return False

    # Reject OCR artifacts with excessive special characters (>30% non-alphanumeric)
    non_alpha = sum(1 for c in t if not c.isalnum() and c not in " &.,'-/")
    if len(t) > 0 and non_alpha / len(t) > 0.3:
        return False

    # Words in company name >= 4 characters must contain at least one vowel
    for tok in comp_tokens:
        clean_tok = re.sub(r"[^a-zA-Z]", "", tok)
        if len(clean_tok) >= 4 and not re.search(r"[aeiouyAEIOUY]", clean_tok):
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
    # Reject currency symbols and compensation / rate patterns (e.g. "$80 - $85 an hour", "€50k", "£40/hr")
    if any(c in t for c in ["$", "€", "£", "₹", "¥", "%"]):
        return False
    if re.search(r"\b(?:hour|an hour|per hour|hourly|salary|annually|per year|w2|c2c|1099|background check|drug test|clearance required)\b", t, re.IGNORECASE):
        return False

    # Reject phone/contact channel noise (e.g. "CTV- Phone", "CTV-", "Phone", "Mobile", "Call", "Email", "Grnail", "Gmai", "Ynai")
    if re.search(r"\b(?:phone|mobile|cell|telephone|call|email|e-mail|gmail|grnail|gmai|ynai|yahoo|hotmail|outlook)\b", t, re.IGNORECASE):
        return False
    if re.match(r"^(?:ctv|tel|ph|fx|mob)[\s\-_:]", t, re.IGNORECASE) or t.lower() in {"ctv-", "ctv", "phone", "email"}:
        return False

    # Reject chat status and system phrases (e.g. "History is on", "Active now", "Turn off history")
    if re.search(r"\b(?:history is on|history is off|active now|offline|online|typing|seen at|last seen|joined the chat)\b", t, re.IGNORECASE):
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
        # Chrome / Browser UI noise
        "ask gemini", "more tools", "new tab", "bookmarks bar",
        "reading list", "side panel", "chrome web store", "customize chrome",
        "admin settings", "find people", "cast to",
        # System tray / taskbar
        "ultraviewer", "teamviewer", "anydesk", "task manager",
    ]
    return any(p in t for p in noise_phrases)


def is_valid_person_name(text: Optional[str]) -> bool:
    """
    Strict Semantic Person Name Validation.
    Validates if a text string is a genuine individual candidate name.
    Rejects:
    - Job Titles ("Facilities Coordinator", "Contract Mid-level", "Senior Engineer")
    - Corporate / Vendor entities ("Cloud Destinations LLC", "InnovaWorkforce Inc", "Fastnet Staffing")
    - UI / Browser / Document artifacts ("All Bookmarks", "Full Job Description", "Business Management Spreadsheets")
    - Text with special symbols ("Qlick Ap*y") or numbers
    - Connection degrees ('· 1st', '2nd'), locations, pronouns, and actions.
    Requires 2 to 4 properly capitalized human name parts.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    # Strip pronouns and connection degree badges first
    t = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd(?:\+)?).*$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    if len(t) < 3 or len(t) > 40:
        return False
    if is_noise_text(t) or is_valid_location(t) or extract_connection_degree(t):
        return False
    if UI_ACTIONS.match(t) or re.search(r"^[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]", t):
        return False

    # A person name cannot contain digits, colons, or punctuation/math/wildcard symbols
    if any(c.isdigit() or c in "*@/\\()_~!+=<>[]{}^%$#:;?\"" for c in t):
        return False

    # Reject truncated strings ending with dots or ellipses e.g. "54 Ri Ht...", "John..."
    if t.endswith(".") or ".." in t:
        return False

    # A person name CANNOT be a job title!
    if is_plausible_title(t):
        return False

    # A person name CANNOT be a company name or contain corporate designators!
    corp_designators = [
        "inc", "llc", "corp", "corporation", "gmbh", "technologies", "technology",
        "solutions", "services", "consulting", "staffing", "workforce", "group",
        "holdings", "partners", "agency", "labs", "software", "international",
        "enterprises", "associates", "associated", "network", "networks", "systems",
        "global", "capital", "ventures", "management", "financial", "company", "companies",
        "college", "university", "institute", "school", "foundation", "queue"
    ]
    if is_valid_company_name(t) and any(re.search(rf"\b{re.escape(d)}\b", t, re.IGNORECASE) for d in corp_designators):
        return False

    # Reject names that start with article 'The ' or UI action 'Review '
    if t.lower().startswith("the ") or t.lower().startswith("review "):
        return False

    # Reject names that end in corporate / agency designations (e.g. "Daley Ard Associates", "The Davis Companies")
    if any(t.lower().endswith(" " + d) for d in [
        "associates", "associated", "partners", "partner", "group", "holdings",
        "solutions", "consulting", "enterprises", "llc", "inc", "corp", "agency",
        "network", "networks", "systems", "ventures", "capital", "companies", "company",
        "college", "university", "queue"
    ]):
        return False

    words = t.split()
    # Filter for alphabetic words (allowing standard hyphens or apostrophes in names e.g. O'Connor, Anne-Marie)
    clean_words = [re.sub(r"[^a-zA-Z\'-]", "", w) for w in words]
    clean_words = [w for w in clean_words if w and any(c.isalpha() for c in w)]
    if len(clean_words) < 2 or len(clean_words) > 4:
        return False
    if any(len(w) < 2 for w in clean_words):
        return False

    # Reject if all words are 2-letter fragments (e.g. "Ri Ht" -> OCR truncation)
    # Real names must have at least one name component with length >= 3
    if all(len(w) <= 2 for w in clean_words):
        return False

    # Reject any string containing unicode replacement character or unprintable chars
    if "\ufffd" in t or "\\ufffd" in t or "\uFFFD" in t:
        return False

    # Every name token with length >= 3 must contain at least one vowel (rejects consonant-only OCR noise e.g. 'Svh', 'Trk')
    if any(len(w) >= 3 and not re.search(r"[aeiouyAEIOUY]", w) for w in clean_words):
        return False

    # Every word must be a valid human name token: Capital letter followed by lowercase letters
    # Accepts: John, Mary-Jane, O'Connor, McDonald, de, van
    for w in clean_words:
        if not w[0].isupper():
            return False
        # Reject ALL-CAPS words that look like acronyms or UI labels (e.g. 'LLC', 'INC', 'D365', 'MDG')
        if len(w) > 2 and w.isupper():
            return False
        # Reject internal uppercase letters that represent OCR glitches (e.g. 'SaO', 'MEkan', 'JaIl', 'LiKe')
        # Allowed exceptions: McDonald, McCarthy, O'Connor
        rest = w[1:]
        if any(c.isupper() for c in rest):
            # Check if valid prefix (Mc, Mac, O')
            is_valid_prefix = bool(re.match(r"^(?:Mc[A-Z][a-z]+|Mac[A-Z][a-z]+|O'[A-Z][a-z]+|[A-Z][a-z]+-[A-Z][a-z]+)$", w))
            if not is_valid_prefix:
                return False

    # Check for non-name title/role/section/system/document words
    lower_words = [w.lower() for w in clean_words]
    blacklisted = {
        # Navigation & UI
        "experience", "education", "skills", "about", "activity", "interests",
        "recommendations", "people", "results", "search", "connections", "followers",
        "director", "recruiter", "manager", "engineer", "sourcer", "specialist",
        "consultant", "analyst", "current", "previous", "view", "contact",
        "university", "college", "institute", "school", "company", "group", "team",
        "inbox", "mail", "gmail", "outlook", "gemini", "chatgpt", "claude", "copilot",
        "chat", "assistant", "jobs", "apply", "feed", "home", "notifications",
        "network", "windows", "tab", "chrome", "firefox", "edge", "safari",
        "microsoft", "teams", "slack", "skype", "webex", "zoom", "technovion",
        "scout", "demand", "lawyers", "lawyer", "legal",
        "prashant", "tiwari", "gaurav", "dwivedi", "muskan", "tushar",
        "yatendra", "rawat", "abhishek", "jadon",
        "post", "posts", "quick", "easy", "prompt", "top", "united", "states",
        "history", "conversation", "conversations", "profile", "profiles",
        "message", "messages", "filter", "filters", "dialog", "session", "menu",
        # Quantitative / Job posting / Adjectives / Agencies
        "minimum", "maximum", "salary", "hourly", "rate", "rates", "contract",
        "total", "average", "standard", "background", "check", "clearance",
        "client", "vendor", "partner", "partners", "overview", "description",
        "associates", "associated",
        # Web / Browser & Document Noise
        "bookmarks", "all", "description", "spreadsheets", "management", "contract",
        "mid-level", "senior", "junior", "full", "part-time", "temporary", "remote",
        "hybrid", "on-site", "overview", "hiring", "job", "career", "careers",
        "talent", "staffing", "recruitment", "employee", "employees", "software",
        "international", "business", "development", "lead", "services", "solutions",
        "destinations", "workforce", "work", "worker", "employment", "document",
        "spreadsheet", "file", "download", "summary", "workflow", "data", "report",
        "candidate", "candidates", "applicant", "applicants", "resume", "cv",
        "open", "closed", "level", "hourly", "salary", "annually", "rate",
        "click", "skip", "badge", "icon", "logo", "search", "google", "meet",
        "tools", "tool", "admin", "settings", "setting", "app", "apps", "more",
        "desktop", "find", "spark", "planet", "seasoned", "tv", "options", "option",
        "device", "devices", "help", "support", "sign", "login", "logout", "portal",
        "zoominfo", "lite", "export", "reveal", "suggest", "homepage",
        "reason", "active", "window", "active window", "overview", "candidate card",
        # Executive role acronyms & tokens
        "cto", "ceo", "cfo", "coo", "cio", "cmo", "cpo", "cro", "vp", "svp", "evp", "hr",
        "myridius",
    }
    if any(w in blacklisted for w in lower_words):
        return False
    if "reason:" in t.lower() or "active window" in t.lower() or "overview" in t.lower():
        return False
    return True


VALID_EMAIL_TLDS = {
    "com", "org", "net", "edu", "gov", "mil", "int",
    "co", "io", "ai", "in", "us", "uk", "ca", "de", "fr", "au",
    "dev", "tech", "xyz", "app", "me", "info", "biz", "eu", "ch",
    "nl", "se", "no", "es", "it", "br", "mx", "jp", "cn", "sg",
    "nz", "ie", "za", "cloud", "agency", "global", "solutions",
    "consulting", "careers", "group", "team", "network", "digital",
    "pro", "online", "site", "live", "world"
}

DISALLOWED_OCR_EMAIL_TLDS = {
    "corn", "can", "ccyn", "eom", "carn", "corr", "coin", "comr",
    "cyn", "con", "corm", "cam", "coom", "vom", "xom"
}


def is_valid_email(email: Optional[str]) -> bool:
    """
    Validates whether an email string is structurally sound and has a legitimate TLD.
    Rejects OCR-garbled emails ending in .corn, .can, .ccyn, .eom, etc.
    """
    if not email or not isinstance(email, str):
        return False
    e = email.strip().lower()
    if len(e) < 6 or len(e) > 100:
        return False
    if not EMAIL_REGEX.match(e):
        return False
    if any(c in e for c in [" ", "\ufffd", "\uFFFD"]):
        return False

    parts = e.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    if len(local) < 1 or len(domain) < 3:
        return False

    # Domain must contain at least one dot
    if "." not in domain:
        return False

    tld = domain.split(".")[-1].strip().lower()
    if tld in DISALLOWED_OCR_EMAIL_TLDS:
        return False
    if tld not in VALID_EMAIL_TLDS:
        return False

    # Domain name before TLD must be at least 2 chars
    domain_name = domain.split(".")[-2]
    if len(domain_name) < 2:
        return False

    return True


EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
PHONE_REGEX = re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{10,14}|\b[2-9]\d{9}\b")


def clean_person_name(text: Optional[str]) -> Optional[str]:
    """
    Strips notification badges (54 |, (54)), degree badges (• 2nd, · 1st), pronouns,
    honorifics (Dr., Mr.), bullets, and validates clean candidate name.
    Example: '54 | Ritik Sharma' -> 'Ritik Sharma'
    Example: '(54) Mariam Nguyen • 2nd' -> 'Mariam Nguyen'
    """
    if not text:
        return None
    raw_str = text.strip()
    # Immediate rejection of key-value / label pairs with colons or truncated strings with ellipses
    if ":" in raw_str or ".." in raw_str or raw_str.endswith("..."):
        return None
    t = raw_str
    # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] "
    t = re.sub(r"^(?:[\(\[]?\d+\+?[\)\]]?\s*[|•·–—\-:]?\s*)+", "", t).strip()
    # Strip degree suffixes: • 2nd, · 1st, 3rd, etc.
    t = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd(?:\+)?).*$", "", t, flags=re.IGNORECASE).strip()
    # Strip pronouns in parens/brackets/free: (she/her), [she/her], (he/him), etc.
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    # Strip honorific prefixes (Dr., Mr., Ms., Mrs., Prof.)
    t = re.sub(r"^(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+", "", t, flags=re.IGNORECASE).strip()
    # Strip trailing badges / dots / icons
    t = re.sub(r"[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$", "", t).strip()
    # Strip professional post-nominal credentials appended to names with commas.
    # e.g. "Kate Threewitts, SPHR, SHRM-SCP" → "Kate Threewitts"
    # e.g. "Megan Alford, PRC, CIR, CMVR" → "Megan Alford"
    # Pattern: comma followed by 2-10 uppercase letters/numbers/hyphens (credential abbreviations)
    t = re.sub(r"(?:,\s*[A-Z][A-Z0-9\-]{1,9})+$", "", t).strip()
    return t if is_valid_person_name(t) else None


