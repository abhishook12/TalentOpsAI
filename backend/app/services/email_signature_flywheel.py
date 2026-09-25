"""
Data Flywheel & Passive Email Signature Mining Engine — TalentOps AI
====================================================================

Extracts high-fidelity recruiter intelligence directly from email sign-offs
and signatures (Direct Cell, Title, Corporate Calendar, LinkedIn, Company).
Feeds discoveries directly into DiscoveryStaging and triggers the continuous
learning flywheel in PostgreSQL.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..models.models import Recruiter, Company, RecruiterPhone
from .scraper import is_human_name

logger = logging.getLogger("talentops.signature_flywheel")

# Sign-off delimiters commonly starting email signatures
SIG_DELIMITERS = [
    re.compile(r'(?:^|\n)\s*--\s*(?:\n|$)', re.MULTILINE),
    re.compile(r'(?:^|\n)\s*_{2,}\s*(?:\n|$)', re.MULTILINE),
    re.compile(r'(?:^|\n)\s*(?:best|best regards|regards|kind regards|warm regards|thanks|thank you|many thanks|sincerely|cheers|respectfully),?\s*\n', re.IGNORECASE | re.MULTILINE),
]

# Phone number patterns with contextual labels
PHONE_LABEL_REGEX = re.compile(
    r'(?:cell|mobile|direct|office|phone|tel|d|m|p)\s*[:.-]?\s*(\+?1?[\s.-]?\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4})',
    re.IGNORECASE
)
GENERAL_PHONE_REGEX = re.compile(
    r'(?:\+?1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'
)

# Corporate calendar booking links
CALENDAR_REGEX = re.compile(
    r'https?://(?:www\.)?(?:calendly\.com|meetings\.hubspot\.com|chilipiper\.com|cal\.com)/[a-zA-Z0-9_\-]+',
    re.IGNORECASE
)

# LinkedIn profiles
LINKEDIN_REGEX = re.compile(
    r'https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)',
    re.IGNORECASE
)

# Recruiter titles in signatures
RECRUITER_TITLES = [
    "Technical Recruiter", "Senior Technical Recruiter", "Lead Recruiter",
    "Executive Recruiter", "Talent Acquisition Specialist", "Talent Acquisition Manager",
    "VP of Talent Acquisition", "Head of Talent", "Director of Recruiting",
    "Staffing Consultant", "Account Executive", "Managing Director", "Principal Recruiter",
    "Recruitment Consultant", "People Operations", "Talent Partner"
]


class EmailSignatureFlywheel:
    """Parses email signatures and feeds the self-reinforcing recruitment data flywheel."""

    def extract_signature_block(self, email_body: str) -> str:
        """Isolates the signature block from the body of an email."""
        if not email_body:
            return ""

        text = email_body.replace("\r\n", "\n")

        # Try to locate sign-off delimiter
        for delimiter in SIG_DELIMITERS:
            match = delimiter.search(text)
            if match:
                # Return the remaining lines after the sign-off delimiter
                sig_part = text[match.end():].strip()
                if len(sig_part) > 10:
                    return sigpart_clean if (sigpart_clean := sig_part[:1200]) else sig_part

        # Fallback: inspect the last 12 lines of text
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) > 4:
            return "\n".join(lines[-10:])
        return text

    def parse_signature(self, signature_text: str, sender_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts structured recruiter profile entities from a signature block.
        Returns: {name, title, company, phone, email, calendar_link, linkedin_url}
        """
        lines = [l.strip() for l in signature_text.split("\n") if l.strip()]
        extracted = {
            "name": None,
            "title": None,
            "company": None,
            "phone": None,
            "email": sender_email,
            "calendar_link": None,
            "linkedin_url": None,
            "raw_signature": signature_text.strip()
        }

        # 1. Direct phone extraction
        phone_match = PHONE_LABEL_REGEX.search(signature_text)
        if phone_match:
            extracted["phone"] = phone_match.group(1).strip()
        else:
            gen_match = GENERAL_PHONE_REGEX.search(signature_text)
            if gen_match:
                extracted["phone"] = gen_match.group(0).strip()

        # 2. Calendar booking link
        cal_match = CALENDAR_REGEX.search(signature_text)
        if cal_match:
            extracted["calendar_link"] = cal_match.group(0).strip()

        # 3. LinkedIn profile
        li_match = LINKEDIN_REGEX.search(signature_text)
        if li_match:
            extracted["linkedin_url"] = f"https://www.linkedin.com/in/{li_match.group(1)}"

        # 4. Email address inside signature if sender_email was not supplied
        if not extracted["email"]:
            email_match = re.search(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', signature_text)
            if email_match:
                extracted["email"] = email_match.group(0).lower().strip()

        # 5. Name and Title extraction from leading signature lines
        for i, line in enumerate(lines[:6]):
            # Skip empty lines or pure phone/link lines
            if re.search(r'https?://|@|cell:|phone:|direct:', line, re.IGNORECASE):
                continue

            # Candidate name heuristics
            tokens = line.split()
            if not extracted["name"] and 2 <= len(tokens) <= 4:
                # Check if line contains a recruiter title rather than a name
                has_title = any(t.lower() in line.lower() for t in RECRUITER_TITLES)
                if not has_title and is_human_name(line, ""):
                    extracted["name"] = line.strip()
                    continue

            # Title heuristics
            if not extracted["title"]:
                for t in RECRUITER_TITLES:
                    if t.lower() in line.lower():
                        extracted["title"] = line.strip()
                        break
                if not extracted["title"] and any(w in line.lower() for w in ["recruiter", "talent", "staffing", "partner", "consultant"]):
                    extracted["title"] = line.strip()

        # 6. Company inference from sender email or signature line
        if extracted["email"] and "@" in extracted["email"]:
            dom = extracted["email"].split("@")[1]
            if dom not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com"):
                extracted["company"] = dom.split(".")[0].title()

        return extracted

    def ingest_signature_profile(self, parsed_profile: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Ingests parsed signature data into DiscoveryStaging and triggers flywheel learning.
        """
        name = parsed_profile.get("name")
        email = parsed_profile.get("email")
        company = parsed_profile.get("company", "Unknown")
        title = parsed_profile.get("title", "Recruiter")
        phone = parsed_profile.get("phone")
        linkedin = parsed_profile.get("linkedin_url")

        if not name or not email:
            return {"success": False, "reason": "Missing required name or email"}

        # 1. Stage in DiscoveryStaging
        import uuid
        import json
        from ..models.auth_models import User

        domain = email.split("@")[1] if "@" in email else ""
        user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
        first_user = db.query(User.id).first()
        owner_id = user.id if user else (first_user[0] if first_user else 1)

        discovery_id = f"SIG-{uuid.uuid4().hex[:16].upper()}"
        batch_id = f"signature_flywheel_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        staging_entry = DiscoveryStaging(
            batch_id=batch_id,
            discovery_id=discovery_id,
            session_id="signature_session",
            device_id="EMAIL_SIGNATURE_FLYWHEEL",
            owner_user_id=owner_id,
            raw_name=name[:200] if name else None,
            raw_email=email[:200] if email else None,
            raw_company=company[:255] if company else None,
            raw_title=title[:200] if title else None,
            raw_phone=phone[:50] if phone else None,
            raw_linkedin=linkedin[:300] if linkedin else None,
            source_url=f"email://{domain}",
            source_page_title=f"Signature: {name}",
            extraction_source="email_signature_flywheel",
            dom_confidence=95,
            processing_status="pending",
            quality_score=95,
            page_type="email_signature",
            metadata_json=json.dumps({
                "source": "signature_flywheel",
                "calendar_link": parsed_profile.get("calendar_link") or "",
                "direct_phone": phone,
                "confidence_score": 95,
            })
        )
        db.add(staging_entry)
        db.flush()

        # 2. Learn company email pattern in PostgreSQL CompanyEmailPattern
        try:
            from .email_intelligence_service import email_intelligence
            email_intelligence.learn_pattern_from_email(email, name, company, db)
        except Exception as learn_err:
            logger.debug("[SIGNATURE_FLYWHEEL] Learning error: %s", learn_err)

        db.commit()
        logger.info("⚡ [SIGNATURE_FLYWHEEL] Successfully mined recruiter from email signature: %s (%s)", name, email)
        return {
            "success": True,
            "staged_id": staging_entry.id,
            "name": name,
            "email": email,
            "company": company,
            "phone": phone
        }


# Singleton instance
email_signature_flywheel = EmailSignatureFlywheel()
