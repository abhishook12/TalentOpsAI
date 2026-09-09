"""
chat_intelligence_pipeline.py — Unified Chat & Unstructured Note Intelligence Pipeline.

Shared pipeline for:
- Google Chat Webhooks / Workspace Apps
- Microsoft Teams Graph API Webhooks / Channel Messages
- Unstructured Recruiter Notes & Copy-Paste Pastes

Key Principles:
1. Lossless Parsing: Extracts raw fragments without fabricating missing identities.
2. Partial Record Staging: Marks partial observations (e.g. "John - 5716175929 - john@abc.com")
   with `is_partial=True` so they never corrupt canonical records.
3. Multi-Pattern Robustness: Handles delimiters (hyphens, colons, pipes, commas, newlines).
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

from .phone_quality_engine import PhoneQualityEngine
from .company_domain_engine import CompanyDomainEngine
from .profile_identity_engine import ProfileIdentityEngine

logger = logging.getLogger("talentops.chat_intelligence")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}(?:\s*(?:ext|x|extension)\s*\d+)?",
    re.IGNORECASE,
)
URL_REGEX = re.compile(r"https?://[^\s<>\"'()]+", re.IGNORECASE)

COMPANY_PREPOSITIONS = re.compile(r"\b(?:at|from|with|@)\s+([A-Z][A-Za-z0-9\s&.,'-]+)", re.IGNORECASE)
TITLE_INDICATORS = re.compile(
    r"\b((?:Senior|Lead|Staff|Principal|Chief|Head of|VP of|Associate|Junior)?\s*"
    r"(?:Product|Engineering|Marketing|Sales|Software|DevOps|Cloud|Infrastructure|Site Reliability|SRE|Full Stack|Frontend|Backend|Data|Security)?\s*"
    r"(?:Engineer|Developer|Architect|Manager|Lead|Director|Specialist|Consultant|Recruiter|Sourcer|Scientist|Officer|Executive|DevOps))\b",
    re.IGNORECASE,
)


class ChatIntelligencePipeline:
    """
    Unified extraction and normalization pipeline for messy recruiter chat notes.
    """

    @classmethod
    def parse_message(
        cls,
        text: Optional[str],
        source_platform: str = "GOOGLE_CHAT",
        sender_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts contact points and entities from unstructured chat text.
        Returns a structured dictionary with partial classification.
        """
        if not text or not str(text).strip():
            return {
                "source_platform": source_platform,
                "is_partial": True,
                "is_empty": True,
                "extracted_fields": {},
                "observations": [],
            }

        raw_text = str(text).strip()

        # 1. Extract Emails
        emails = EMAIL_REGEX.findall(raw_text)
        primary_email = emails[0] if emails else None

        # 2. Extract Phones
        raw_phones = PHONE_REGEX.findall(raw_text)
        valid_phones = []
        for p in raw_phones:
            v = PhoneQualityEngine.validate_and_format(p)
            if v["is_valid"]:
                valid_phones.append(v)

        primary_phone_obj = valid_phones[0] if valid_phones else None
        primary_phone = primary_phone_obj["e164"] if primary_phone_obj else None

        # 3. Extract URLs & Social Profiles
        urls = URL_REGEX.findall(raw_text)
        linkedin_url = None
        for u in urls:
            norm_profile = ProfileIdentityEngine.normalize_profile_url(u)
            if norm_profile["platform"] == "LINKEDIN" and norm_profile["is_valid"]:
                linkedin_url = norm_profile["canonical_url"]
                break

        # 4. Extract Company (via prepositions: 'at Acme', 'from Datadog')
        company = None
        comp_match = COMPANY_PREPOSITIONS.search(raw_text)
        if comp_match:
            cand_comp = comp_match.group(1).strip()
            # Trim trailing punctuation or conjunctions
            cand_comp = re.split(r"[,;|\n\-]", cand_comp)[0].strip()
            company = CompanyDomainEngine.clean_company_name(cand_comp)

        # Company domain derivation from email
        company_domain = None
        if primary_email:
            domain = CompanyDomainEngine.extract_domain_from_email(primary_email)
            if domain and CompanyDomainEngine.is_corporate_domain(domain):
                company_domain = domain

        # 5. Extract Title
        title = None
        title_match = TITLE_INDICATORS.search(raw_text)
        if title_match:
            title = title_match.group(1).strip()

        # 6. Extract Name
        # Heuristic: Find words before delimiters (-, |, :) or before email/phone
        name = cls._extract_candidate_name(raw_text, primary_email, primary_phone_obj["raw"] if primary_phone_obj else None)

        # 7. Classify completeness & partial status
        has_full_name = bool(name and len(name.split()) >= 2)
        has_contact = bool(primary_email or primary_phone)
        is_partial = not (has_full_name and has_contact and (company or title))

        extracted_fields = {
            "name": name,
            "has_full_name": has_full_name,
            "current_company": company,
            "company_domain": company_domain,
            "current_title": title,
            "primary_email": primary_email,
            "all_emails": emails,
            "primary_phone": primary_phone,
            "phone_details": primary_phone_obj,
            "linkedin_url": linkedin_url,
            "raw_notes": raw_text,
        }

        # Build field-level observations
        observations = []
        source_weight = 0.76 if source_platform in ("GOOGLE_CHAT", "MICROSOFT_TEAMS") else 0.70

        if name:
            observations.append({
                "field_name": "full_name",
                "field_value": name,
                "confidence": 0.85 if has_full_name else 0.65,
                "source": source_platform,
            })
        if primary_email:
            observations.append({
                "field_name": "primary_email",
                "field_value": primary_email,
                "confidence": 0.90,
                "source": source_platform,
            })
        if primary_phone:
            observations.append({
                "field_name": "primary_phone",
                "field_value": primary_phone,
                "confidence": primary_phone_obj["confidence"] if primary_phone_obj else 0.85,
                "source": source_platform,
            })
        if company:
            observations.append({
                "field_name": "current_company",
                "field_value": company,
                "confidence": 0.75,
                "source": source_platform,
            })
        if title:
            observations.append({
                "field_name": "current_title",
                "field_value": title,
                "confidence": 0.75,
                "source": source_platform,
            })
        if linkedin_url:
            observations.append({
                "field_name": "linkedin_url",
                "field_value": linkedin_url,
                "confidence": 0.95,
                "source": source_platform,
            })

        return {
            "source_platform": source_platform,
            "is_partial": is_partial,
            "is_empty": False,
            "confidence_score": cls._calculate_confidence(extracted_fields),
            "extracted_fields": extracted_fields,
            "observations": observations,
            "sender_info": sender_info or {},
        }

    @classmethod
    def _extract_candidate_name(
        cls,
        text: str,
        primary_email: Optional[str],
        raw_phone: Optional[str],
    ) -> Optional[str]:
        """
        Carefully extracts candidate name without fabricating.
        Handles: 'John - 5716175929', 'Sarah from Datadog', 'David Miller | Engineer'
        """
        # Split into segments by standard delimiters, treating parenthesized blocks as delimiters
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        first_line = lines[0] if lines else text

        normalized_line = re.sub(r"\(.*?\)", " | ", first_line)
        segments = re.split(r"[\-|:,•|]", normalized_line)
        for seg in segments:
            candidate = seg.strip()
            # If segment is the email or phone, skip
            if primary_email and primary_email in candidate:
                continue
            if raw_phone and raw_phone in candidate:
                continue
            # Remove filler words
            clean_cand = re.sub(r"^(?:candidate|lead|name|contact|met with|talked to|spoke with|profile)\s*[:\-]?\s*", "", candidate, flags=re.IGNORECASE).strip()
            # Check if it has "from Company", "at Company", or "regarding Role"
            clean_cand = re.sub(r"\s+(?:at|from|with|@|regarding|re:?|for)\s+.*$", "", clean_cand, flags=re.IGNORECASE).strip()

            # Verify it looks like a person's name (1 to 4 alphabetical words, no numbers)
            words = clean_cand.split()
            if 1 <= len(words) <= 4 and all(w.replace(".", "").isalpha() for w in words):
                if not any(TITLE_INDICATORS.search(w) for w in words):
                    return " ".join(w.capitalize() for w in words)

        return None

    @classmethod
    def _calculate_confidence(cls, fields: Dict[str, Any]) -> float:
        score = 0.0
        if fields.get("name"):
            score += 0.30 if fields.get("has_full_name") else 0.15
        if fields.get("primary_email"):
            score += 0.35
        if fields.get("primary_phone"):
            score += 0.20
        if fields.get("current_company"):
            score += 0.10
        if fields.get("current_title"):
            score += 0.05
        return min(1.0, score)
