"""
extractor/parsers/linkedin_parser.py — LinkedIn Modular Parser (Standard, Recruiter, Sales Nav)
"""

from __future__ import annotations
import re
import urllib.parse
from typing import Dict, Any, Optional, List
from .base_parser import BasePlatformParser
from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    clean_title_and_company,
    clean_job_title,
    classify_semantic_entity,
    clean_location_text,
    is_valid_location,
    is_plausible_title,
    is_valid_email,
    EMAIL_REGEX,
    PHONE_REGEX,
)
from scout_desktop.extractor.field_classifier import FieldClassifier


class LinkedInParser(BasePlatformParser):
    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    def can_handle(self, url: str, platform_hint: str, window_title: str) -> bool:
        u = (url or "").lower()
        p = (platform_hint or "").lower()
        t = (window_title or "").lower()
        if "linkedin.com" in u or "linkedin" in p or "linkedin" in t:
            return True
        return False

    def detect_page_type(self, ocr_text: str, url: str, window_title: str) -> str:
        u = (url or "").lower()
        t = (window_title or "").lower()
        text_low = (ocr_text or "").lower()

        if "/jobs/" in u or "about the job" in text_low or "job details" in text_low:
            return "JOB_POSTING"
        if "/company/" in u or "/school/" in u or ": people" in t or ": overview" in t or ": about" in t or ": jobs" in t or ": life" in t:
            return "COMPANY_PAGE"
        if "/messaging/" in u or "- messaging" in t:
            return "MESSAGING_THREAD"
        if "/search/results/" in u or "see all results" in text_low or "people who also viewed" in text_low and "/in/" not in u:
            return "SEARCH_RESULTS"
        if "/in/" in u or "sales/lead/" in u or "recruiter/profile/" in u:
            return "PROFILE_PAGE"

        # Content signature detection for profile header
        has_profile_sections = any(sec in text_low for sec in ("experience", "about", "activity", "education", "skills", "contact info"))
        if has_profile_sections and (" | linkedin" in t or "linkedin" in t):
            return "PROFILE_PAGE"

        return "PROFILE_PAGE" if "linkedin" in t else "UNKNOWN"

    def parse(self, ocr_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        page_url = context.get("source_url", "")
        win_title = context.get("window_title", "")
        page_type = self.detect_page_type(ocr_text, page_url, win_title)

        if page_type in ("JOB_POSTING", "COMPANY_PAGE", "MESSAGING_THREAD"):
            return None  # Non-candidate contexts

        lines = [ln.strip() for ln in (ocr_text or "").split("\n") if ln.strip()]
        if not lines:
            return None

        name = None
        title = None
        company = None
        location = None
        email = None
        phone = None

        # 1. Try window title extraction for name (e.g. "Elizabeth Bowers | LinkedIn - Google Chrome")
        m_title = re.match(r"^(?:\(\d+\+?\)\s*)?([^|•·\n]+?)\s*[|•·]\s*LinkedIn", win_title, re.IGNORECASE)
        if m_title:
            cand_from_title = clean_person_name(m_title.group(1).strip())
            if cand_from_title and is_valid_person_name(cand_from_title):
                name = cand_from_title

        # 2. Extract from OCR lines (Header block heuristic)
        # In LinkedIn, line 0 or line 1 is usually the name, followed by headline (title at company), then location
        name_idx = -1
        if name:
            expected = name.casefold()
            for i, line in enumerate(lines[:8]):
                cleaned = clean_person_name(line)
                if cleaned and cleaned.casefold() == expected:
                    name_idx = i
                    break
        else:
            for i, line in enumerate(lines[:8]):
                # Ignore navigation lines
                if any(nav in line.lower() for nav in ("feed", "mynetwork", "jobs", "messaging", "notifications", "search", "skip to")):
                    continue
                cleaned = clean_person_name(line)
                if cleaned and is_valid_person_name(cleaned):
                    name = cleaned
                    name_idx = i
                    break

        # If name found in OCR lines, inspect subsequent lines for Title and Company
        if name_idx >= 0:
            for line in lines[name_idx + 1 : name_idx + 6]:
                # Parse headline (e.g. "Senior Technical Recruiter at Amazon" or "Staff Product Designer | Figma | Design Systems")
                t_cand, c_cand = clean_title_and_company(line)
                if not title and t_cand and is_plausible_title(t_cand):
                    title = t_cand
                if not company and c_cand:
                    c_clean = clean_company_name(c_cand)
                    if c_clean and is_valid_company_name(c_clean) and classify_semantic_entity(c_clean).get("entity_type") == "COMPANY":
                        company = c_clean
                elif not title and is_plausible_title(line):
                    title = clean_job_title(line) or line.strip()
                elif not location:
                    loc_cand = clean_location_text(line)
                    if loc_cand and is_valid_location(loc_cand):
                        location = loc_cand
                elif title and not company and not is_plausible_title(line) and not is_valid_location(line):
                    co = clean_company_name(line)
                    if co and is_valid_company_name(co):
                        se = classify_semantic_entity(co)
                        if se.get("entity_type") == "COMPANY" and se.get("confidence", 0) >= 0.90:
                            company = co

        education = None
        header_fields = {}
        if name and "/in/" in page_url:
            for idx, line in enumerate(lines):
                if not re.fullmatch(re.escape(name) + r"(?:\s*(?:\d+(?:st|nd|rd|th)\+?|[@✓✔·•].*))?", line, re.I):
                    continue
                header = []
                for item in lines[idx + 1:idx + 18]:
                    if re.match(r"^(?:more profiles|people you|promoted|about$|activity$|https?:|linkedin\.com)", item, re.I):
                        break
                    # Reject social-proof noise lines that must never become a company or any field
                    if re.match(r"^(?:followed\s+by|mutual\s+connections?|\d+\s*connections?|connections?\s+in\s+common|people\s+you\s+may)", item, re.I):
                        continue
                    # Strip "+ N more" affiliation suffix before storing
                    item = re.sub(r"\s*\+\s*\d+\s+more\b.*$", "", item, flags=re.I).strip()
                    if item:
                        header.append(item)
                for pos, item in enumerate(header):
                    if re.search(r"\bcontact info\b", item, re.I):
                        place = clean_location_text(item)
                        if place:
                            location = place
                    elif not location and is_valid_location(item):
                        place = clean_location_text(item)
                        if place:
                            location = place
                    if re.search(r"\b(?:university|college|polytechnic)\b", item, re.I):
                        education = item
                        if item.casefold().endswith(" of") and pos + 1 < len(header):
                            education += " " + header[pos + 1]
                        if not company and pos and not re.search(r"connections?|message|follow|degree|pg dip", header[pos-1], re.I):
                            cand_co = clean_company_name(header[pos-1])
                            if cand_co and (is_valid_company_name(cand_co) or lines.count(cand_co) > 1 or FieldClassifier.extract_linkedin_affiliation_company([cand_co, item])):
                                company = cand_co
                                header_fields["company"] = company
                        break
                if header and re.search(r"\b(?:engineer(?:ing)?|manager|consultant|professional|director|recruiter|analyst)\b", header[0], re.I):
                    title = re.split(r"\s+(?:I|\||\bat\b)\s+|\s*@", header[0], maxsplit=1, flags=re.I)[0].strip()
                    header_fields["title"] = title
                    employer = re.search(r"(?:@|\bat\b)\s*([\w&.-]+(?: [\w&.-]+)*?)(?:\s+[I|]\s|$)", header[0], re.I)
                    if employer:
                        company = employer[1].strip()
                        header_fields["company"] = company
                    elif not company:
                        for pos, item in enumerate(header[1:], 1):
                            if re.search(r"contact info", item, re.I):
                                break
                            wrapped_headline = header[pos-1].endswith((" |", " I"))
                            before_location = pos + 1 < len(header) and "contact info" in header[pos+1].casefold()
                            # Accept line immediately before location as company if:
                            # (a) headline wraps onto it, or (b) it passes company validation on its own
                            # This catches LinkedIn affiliation pills like "Temporary Staffing Professionals"
                            if before_location and is_valid_company_name(item):
                                company = item
                                header_fields["company"] = company
                                break
                            if wrapped_headline and before_location and is_valid_company_name(item):
                                company = item
                                header_fields["company"] = company
                                break
                break

        if not company:
            rail_comp = FieldClassifier.extract_linkedin_affiliation_company(lines[:16])
            if rail_comp:
                company = rail_comp
                header_fields["company"] = company

        # Regex scan for emails and phones anywhere in profile text
        for line in lines:
            if not email:
                em = EMAIL_REGEX.search(line)
                if em and is_valid_email(em.group(0)):
                    email = em.group(0).lower()
            if not phone:
                ph = PHONE_REGEX.search(line)
                if ph and len(re.sub(r"\D", "", ph.group(0))) >= 10:
                    phone = ph.group(0).strip()

        # Canonical Profile URL
        canonical_url = page_url if "linkedin.com/in/" in page_url else None

        if not name:
            return None

        # Hard Invariant: A person's job title cannot be identical to their own name
        if title and name and title.strip().lower() == name.strip().lower():
            title = None

        # Hard Invariant: A candidate's employer cannot be LinkedIn or a job platform
        from scout_desktop.extractor.patterns import PLATFORM_NAMES
        if company and company.strip().lower() in PLATFORM_NAMES:
            company = None

        return {
            "recruiter_name": name,
            "canonical_name": name,
            "title": title,
            "company_name": company,
            "location": location,
            "education": education,
            "header_fields": header_fields,
            "email": email,
            "phone": phone,
            "platform": "LinkedIn",
            "page_type": page_type,
            "canonical_profile_url": canonical_url,
            "source_url": page_url,
        }
