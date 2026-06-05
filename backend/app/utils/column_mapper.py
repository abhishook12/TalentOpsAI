from typing import List, Dict
import re

# Keyword dictionaries for heuristic column detection
COLUMN_KEYWORDS: Dict[str, List[str]] = {
    "name": ["name", "full_name", "recruiter_name", "candidate_name", "contact_name"],
    "email": ["email", "mail", "email_id", "work_email", "personal_email"],
    "email2": ["email2", "alt_email", "alternate_email", "secondary_email"],
    "email3": ["email3", "third_email"],
    "email4": ["email4", "fourth_email"],
    "phone": ["phone", "mobile", "cell", "contact", "phone_number", "mobile_number"],
    "phone2": ["phone2", "alt_phone", "alternate_phone", "secondary_phone"],
    "phone3": ["phone3", "third_phone"],
    "phone4": ["phone4", "fourth_phone"],
    "company": ["company", "organization", "vendor", "client", "employer"],
    "location": ["location", "city", "address", "address_line", "office_location"],
    "state": ["state", "state_abbr", "province", "region"],
    "linkedin": ["linkedin", "linkedin_url", "profile_link", "profile_url"],
    "title": ["title", "role", "position", "job_title", "designation"],
    "specialization": ["specialization", "skills", "expertise", "focus_area"],
    "notes": ["notes", "remarks", "comments", "additional_info"],
}

def normalise(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())

def detect_columns(headers: List[str]) -> Dict[str, str]:
    """Return a mapping from logical field names to the best‑matching column header.
    If multiple headers match the same logical field, the first seen is chosen.
    """
    mapping: Dict[str, str] = {}
    normalised_headers = {normalise(h): h for h in headers}
    for logical, keywords in COLUMN_KEYWORDS.items():
        for kw in keywords:
            kw_norm = normalise(kw)
            # Direct exact match
            if kw_norm in normalised_headers:
                mapping[logical] = normalised_headers[kw_norm]
                break
            # Fuzzy containment: header contains keyword string
            for nh, original in normalised_headers.items():
                if kw_norm in nh:
                    mapping[logical] = original
                    break
            if logical in mapping:
                break
    return mapping
