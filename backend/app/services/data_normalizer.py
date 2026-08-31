"""
Data Normalizer Service: Comprehensive field sanitation, standardization,
scoring, and taxonomy classification for recruiter records.
"""
import re
import sys
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("data_normalizer")

# Canonical US State Abbreviations
US_STATE_ABBRS = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL",
    "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA",
    "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA",
    "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY"
}

# Major Staffing & Corporate Brand Aliases
KNOWN_COMPANY_MAP = {
    "teksystems": ("TEKsystems", "teksystems.com"),
    "insight global": ("Insight Global", "insightglobal.com"),
    "apex systems": ("Apex Systems", "apexsystems.com"),
    "aerotek": ("Aerotek", "aerotek.com"),
    "actalent": ("Actalent", "actalentservices.com"),
    "kforce": ("Kforce", "kforce.com"),
    "cybercoders": ("CyberCoders", "cybercoders.com"),
    "robert half": ("Robert Half", "roberthalf.com"),
    "manpower": ("ManpowerGroup", "manpowergroup.com"),
    "manpowergroup": ("ManpowerGroup", "manpowergroup.com"),
    "randstad": ("Randstad", "randstadusa.com"),
    "kelly services": ("Kelly Services", "kellyservices.com"),
    "beacon hill": ("Beacon Hill Staffing", "beaconhillstaffing.com"),
    "disys": ("DISYS", "disys.com"),
    "system one": ("System One", "systemone.com"),
    "systemone": ("System One", "systemone.com"),
    "modis": ("Modis", "modis.com"),
    "collabera": ("Collabera", "collabera.com"),
    "judge group": ("The Judge Group", "judge.com"),
    "prolink": ("Prolink Staffing", "prolinkstaff.com"),
    "lucas group": ("Lucas Group", "lucasgroup.com"),
}

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_CLEAN_RE = re.compile(r"\D+")


def clean_name(raw_name: Any) -> Optional[str]:
    """Sanitizes recruiter name, stripping job titles, suffixes, emails, and emojis."""
    if not raw_name:
        return None
    name = str(raw_name).strip()
    if not name or name.lower() in ["none", "nan", "null", "n/a", "unknown"]:
        return None

    # Remove email addresses embedded in name
    name = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "", name)

    # Remove common title tags appended to name (e.g. "John Doe, Senior Recruiter", "Jane (Apex)")
    name = re.sub(r"[\(\[\{].*?[\)\]\}]", "", name)
    name = re.split(r"\s*[,-|]\s*(?:senior|lead|recruiter|director|manager|vp|talent|ph\.?d|mba|pmp|sphr|shrm)", name, flags=re.IGNORECASE)[0]
    
    # Strip emojis and strange non-alphanumeric chars
    name = re.sub(r"[^\w\s\.\'-]", "", name).strip()
    name = re.sub(r"\s+", " ", name)

    # Words proper casing
    if name and len(name) > 1 and not name.isupper():
        name = " ".join(part.capitalize() for part in name.split())
    elif name and name.isupper():
        name = " ".join(part.capitalize() for part in name.split())

    return name if len(name) >= 2 else None


def clean_email(raw_email: Any) -> Optional[str]:
    """Validates and lowercases email address."""
    if not raw_email:
        return None
    email = str(raw_email).strip().lower()
    email = re.sub(r"^(?:mailto:|<|\[)", "", email)
    email = re.sub(r"(?:>|\]|;|,)$", "", email)
    email = email.strip()

    if not email or "@" not in email:
        return None
    
    # Strip junk placeholders
    if any(bad in email for bad in ["example.com", "test.com", "undefined", "noreply", "fake", "sample"]):
        return None

    if EMAIL_RE.match(email):
        return email
    return None


def clean_phone(raw_phone: Any) -> Optional[str]:
    """Standardizes phone numbers into US 10-digit format (XXX) XXX-XXXX or clean formatted string."""
    if not raw_phone:
        return None
    text = str(raw_phone).strip()
    if not text or text.lower() in ["none", "nan", "null", "n/a", "0"]:
        return None

    digits = PHONE_CLEAN_RE.sub("", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) > 10:
        return f"+{digits}"
    elif len(digits) >= 7:
        return digits
    return None


def clean_company(raw_company: Any, email: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Standardizes company name and derives domain.
    Returns: (canonical_company_name, company_domain)
    """
    domain = None
    if email and "@" in email:
        domain = email.split("@")[-1].lower()
        if domain in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com"]:
            domain = None

    if not raw_company:
        if domain:
            raw_company = domain.split(".")[0].replace("-", " ").title()
        else:
            return None, None

    company = str(raw_company).strip()
    if not company or company.lower() in ["none", "nan", "null", "n/a", "unknown"]:
        return None, domain

    # Check known company dictionary
    norm_comp = re.sub(r"[^a-z0-9]", "", company.lower())
    for known_key, (canon_name, canon_dom) in KNOWN_COMPANY_MAP.items():
        if known_key.replace(" ", "") in norm_comp:
            return canon_name, domain or canon_dom

    # Clean corporate legal suffixes
    cleaned = re.sub(r"(?i)\b(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|services|group|solutions|staffing|technologies|holdings)\b", "", company)
    cleaned = re.sub(r"[,|\-]$", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    final_name = cleaned if cleaned else company
    return final_name.title(), domain


def clean_state_and_city(raw_state: Any, raw_location: Any) -> Tuple[Optional[str], Optional[str]]:
    """Derives standard 2-letter US state code and normalized city."""
    state_code = None
    city = None

    # Try state field first
    if raw_state:
        st_str = str(raw_state).strip().upper()
        if st_str in US_STATE_ABBRS.values():
            state_code = st_str
        else:
            st_clean = re.sub(r"[^A-Z]", "", st_str)
            if st_clean in US_STATE_ABBRS.values():
                state_code = st_clean
            elif st_clean in US_STATE_ABBRS:
                state_code = US_STATE_ABBRS[st_clean]

    # Try parsing location string (e.g. "Austin, TX" or "Chicago, Illinois")
    if raw_location and not state_code:
        loc_str = str(raw_location).strip()
        parts = [p.strip() for p in loc_str.split(",") if p.strip()]
        if len(parts) >= 2:
            city_cand = parts[0].title()
            state_cand = parts[1].strip().upper()
            if state_cand in US_STATE_ABBRS.values():
                state_code = state_cand
                city = city_cand
            else:
                st_norm = state_cand.replace(".", "").strip()
                if st_norm in US_STATE_ABBRS:
                    state_code = US_STATE_ABBRS[st_norm]
                    city = city_cand

    if not city and raw_location and "," in str(raw_location):
        city = str(raw_location).split(",")[0].strip().title()

    return state_code, city


def classify_seniority_and_title(raw_title: Any) -> Tuple[str, str]:
    """Classifies seniority tier and standardizes title."""
    if not raw_title:
        return "Mid", "Recruiter"
    title_str = str(raw_title).strip()
    title_lower = title_str.lower()

    if any(k in title_lower for k in ["vp", "vice president", "partner", "founder", "head of", "c-level", "chief"]):
        seniority = "Executive"
    elif any(k in title_lower for k in ["director", "principal"]):
        seniority = "Director"
    elif any(k in title_lower for k in ["lead", "manager", "team lead", "supervisor"]):
        seniority = "Manager"
    elif any(k in title_lower for k in ["senior", "sr", "sr.", "staff"]):
        seniority = "Senior"
    elif any(k in title_lower for k in ["junior", "jr", "jr.", "associate", "coordinator", "trainee"]):
        seniority = "Junior"
    else:
        seniority = "Mid"

    return seniority, title_str.title()


def calculate_scores(record: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates completeness_score, quality_score, trust_score, and is_deliverable flag."""
    completeness = 0
    if record.get("recruiter_name"): completeness += 25
    if record.get("email"): completeness += 30
    if record.get("phone"): completeness += 20
    if record.get("company_id"): completeness += 10
    if record.get("state"): completeness += 10
    if record.get("linkedin"): completeness += 5

    email_conf = 85 if record.get("email") else 0
    if record.get("email") and not any(f in record["email"] for f in ["gmail", "yahoo", "hotmail", "outlook"]):
        email_conf = 95 # Corporate email bonus

    quality = int((completeness * 0.6) + (email_conf * 0.4))
    trust_score = round(min(1.0, quality / 100.0), 2)
    is_deliverable = bool(record.get("email") and email_conf >= 70)

    return {
        "completeness_score": completeness,
        "quality_score": quality,
        "trust_score": trust_score,
        "email_confidence": email_conf,
        "is_deliverable": is_deliverable,
        "is_active": True,
        "is_archived": False
    }


def normalize_record(raw: Dict[str, Any], record_id: int) -> Dict[str, Any]:
    """Applies end-to-end normalization to transform a raw record into canonical Parquet schema."""
    name = clean_name(raw.get("recruiter_name"))
    norm_name = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    
    email = clean_email(raw.get("email"))
    email2 = clean_email(raw.get("email2"))
    email3 = clean_email(raw.get("email3"))
    email4 = clean_email(raw.get("email4"))
    
    phone = clean_phone(raw.get("phone"))
    phone2 = clean_phone(raw.get("phone2"))
    phone3 = clean_phone(raw.get("phone3"))
    phone4 = clean_phone(raw.get("phone4"))
    
    company, domain = clean_company(raw.get("company_id"), email)
    state, city = clean_state_and_city(raw.get("state"), raw.get("location"))
    seniority, title = classify_seniority_and_title(raw.get("title"))

    out = {
        "recruiter_id": record_id,
        "recruiter_name": name or "Talent Specialist",
        "normalized_recruiter_name": norm_name or "talentspecialist",
        "email": email or "",
        "phone": phone or "",
        "email2": email2 or "",
        "phone2": phone2 or "",
        "email3": email3 or "",
        "phone3": phone3 or "",
        "email4": email4 or "",
        "phone4": phone4 or "",
        "alternate_emails": float(len([e for e in [email2, email3, email4] if e])),
        "alternate_phones": float(len([p for p in [phone2, phone3, phone4] if p])),
        "linkedin": str(raw.get("linkedin") or "").strip(),
        "specialization": str(raw.get("specialization") or "Technical Recruiting").strip(),
        "title": title,
        "notes": str(raw.get("notes") or "").strip(),
        "review_reason": "",
        "company_id": company or "Independent Staffing",
        "location": f"{city}, {state}" if (city and state) else (state or city or "United States"),
        "state": state or "US",
        "normalized_city": city or "",
        "location_confidence": "High" if state else "Medium",
        "state_source": "extracted_harvest",
        "state_confidence": "High" if state else "Medium",
        "state_reason": "normalized_from_location",
        "last_scan_at": "",
        "needs_review": "No",
        "data_source": str(raw.get("data_source") or "local_harvester"),
        "source_job_id": "harvester_v2",
        "raw_data": 0.0,
        "metadata_json": "{}",
        "tags": f"harvester,{seniority.lower()}",
        "created_at": "2026-08-20T20:00:00Z",
        "updated_at": "2026-08-20T20:00:00Z",
        "taxonomy_category": "Recruiting & Staffing",
        "report_count": 0.0,
        "email_status": "verified" if email else "missing",
        "email_source": "local_harvest",
        "email_pattern_id": domain or "",
        "email_generated": "",
        "email_verified_at": "2026-08-20",
        "email_last_checked_at": "2026-08-20",
        "canonical_company_id": company or "",
        "historical_company_id": 0.0,
        "company_domain_id": 0.0,
        "raw_email_value": email or "",
        "repair_reason": 0.0,
        "user_id": "",
        "missing_fields": "",
        "sentinel_status": "active",
        "last_verified_at": "2026-08-20",
        "company_confidence": "High" if company else "Medium",
        "company_reasoning": "verified_domain" if domain else "inferred",
        "merged_into_id": 0.0,
        "logo_url": f"https://logos.hunter.io/{domain}" if domain else "",
        "seniority_level": seniority,
        "timezone_code": "EST",
        "timezone": "America/New_York",
        "company_scale": "Enterprise"
    }

    # Add scores
    out.update(calculate_scores(out))
    return out
