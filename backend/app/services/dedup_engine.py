"""
Deduplication Engine: Multi-key entity resolution and non-destructive record merging.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("dedup_engine")


def extract_linkedin_handle(url: str) -> Optional[str]:
    """Extracts normalized handle from linkedin URL."""
    if not url:
        return None
    url_clean = str(url).strip().lower()
    match = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", url_clean)
    if match:
        return match.group(1)
    return None


class DeduplicationEngine:
    """Multi-tier deduplicator that merges candidate and recruiter records."""

    def __init__(self):
        self.by_email: Dict[str, Dict[str, Any]] = {}
        self.by_linkedin: Dict[str, Dict[str, Any]] = {}
        self.by_name_comp_state: Dict[str, Dict[str, Any]] = {}
        self.by_phone: Dict[str, Dict[str, Any]] = {}
        self.merged_records: List[Dict[str, Any]] = []

        self.stats = {
            "total_processed": 0,
            "merged_email": 0,
            "merged_linkedin": 0,
            "merged_name_company": 0,
            "merged_phone": 0,
            "unique_records": 0
        }

    def process_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes a stream or batch of normalized records and returns deduplicated master list."""
        for r in records:
            self.add_or_merge(r)
        
        self.stats["unique_records"] = len(self.merged_records)
        logger.info(
            f"Deduplication complete: {self.stats['total_processed']:,} incoming -> "
            f"{self.stats['unique_records']:,} unique (Email merges: {self.stats['merged_email']:,}, "
            f"LinkedIn merges: {self.stats['merged_linkedin']:,}, "
            f"Name+Company merges: {self.stats['merged_name_company']:,})"
        )
        return self.merged_records

    def add_or_merge(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Checks existing indices for duplicate candidates and performs non-destructive merge."""
        self.stats["total_processed"] += 1
        existing = None
        match_type = None

        email = (record.get("email") or "").strip().lower()
        linkedin = record.get("linkedin") or ""
        li_handle = extract_linkedin_handle(linkedin)
        norm_name = record.get("normalized_recruiter_name") or ""
        comp = (record.get("canonical_company_id") or record.get("company_id") or "").lower().strip()
        state = (record.get("state") or "").upper().strip()
        phone = record.get("phone") or ""
        clean_phone_digits = re.sub(r"\D+", "", phone) if len(phone) >= 7 else ""

        # 1. Tier 1 Match: Email
        if email and email in self.by_email:
            existing = self.by_email[email]
            match_type = "email"
            self.stats["merged_email"] += 1

        # 2. Tier 2 Match: LinkedIn
        elif li_handle and li_handle in self.by_linkedin:
            existing = self.by_linkedin[li_handle]
            match_type = "linkedin"
            self.stats["merged_linkedin"] += 1

        # 3. Tier 3 Match: Name + Company + State
        elif norm_name and comp and state and len(norm_name) > 3 and len(comp) > 2 and state != "US":
            ncs_key = f"{norm_name}::{comp}::{state}"
            if ncs_key in self.by_name_comp_state:
                existing = self.by_name_comp_state[ncs_key]
                match_type = "name_company"
                self.stats["merged_name_company"] += 1

        # 4. Tier 4 Match: Phone (only if 10 distinct digits and not common toll-free)
        elif len(clean_phone_digits) == 10 and not clean_phone_digits.startswith(("800", "888", "877", "866", "855")):
            if clean_phone_digits in self.by_phone:
                existing = self.by_phone[clean_phone_digits]
                match_type = "phone"
                self.stats["merged_phone"] += 1

        if existing:
            # Perform non-destructive enrichment
            self._merge_into(existing, record)
            return existing
        else:
            # New unique record
            self.merged_records.append(record)
            self._index_record(record)
            return record

    def _index_record(self, record: Dict[str, Any]):
        """Adds record to fast lookup indices."""
        email = (record.get("email") or "").strip().lower()
        if email:
            self.by_email[email] = record

        li_handle = extract_linkedin_handle(record.get("linkedin") or "")
        if li_handle:
            self.by_linkedin[li_handle] = record

        norm_name = record.get("normalized_recruiter_name") or ""
        comp = (record.get("canonical_company_id") or record.get("company_id") or "").lower().strip()
        state = (record.get("state") or "").upper().strip()
        if norm_name and comp and state and len(norm_name) > 3 and len(comp) > 2 and state != "US":
            self.by_name_comp_state[f"{norm_name}::{comp}::{state}"] = record

        phone = record.get("phone") or ""
        clean_phone_digits = re.sub(r"\D+", "", phone) if len(phone) >= 7 else ""
        if len(clean_phone_digits) == 10 and not clean_phone_digits.startswith(("800", "888", "877", "866", "855")):
            self.by_phone[clean_phone_digits] = record

    def _merge_into(self, target: Dict[str, Any], incoming: Dict[str, Any]):
        """Merges incoming record into target record without overwriting verified values."""
        # 1. Fill missing core fields
        for field in ["recruiter_name", "normalized_recruiter_name", "title", "company_id", "canonical_company_id", "specialization", "logo_url"]:
            if not target.get(field) and incoming.get(field):
                target[field] = incoming[field]

        # 2. Upgrade LinkedIn
        if not target.get("linkedin") and incoming.get("linkedin"):
            target["linkedin"] = incoming["linkedin"]
            li_h = extract_linkedin_handle(incoming["linkedin"])
            if li_h:
                self.by_linkedin[li_h] = target

        # 3. Upgrade location if target is generic
        if target.get("state") in ["US", "", None] and incoming.get("state") not in ["US", "", None]:
            target["state"] = incoming["state"]
            target["location"] = incoming["location"]
            target["normalized_city"] = incoming["normalized_city"]

        # 4. Multi-phone slotting
        incoming_phone = incoming.get("phone")
        if incoming_phone and incoming_phone != target.get("phone"):
            # Check if already in phone2, phone3, phone4
            existing_phones = {target.get("phone"), target.get("phone2"), target.get("phone3"), target.get("phone4")}
            if incoming_phone not in existing_phones:
                if not target.get("phone2"):
                    target["phone2"] = incoming_phone
                elif not target.get("phone3"):
                    target["phone3"] = incoming_phone
                elif not target.get("phone4"):
                    target["phone4"] = incoming_phone
                target["alternate_phones"] = float(len([p for p in [target.get("phone2"), target.get("phone3"), target.get("phone4")] if p]))

        # 5. Multi-email slotting
        incoming_email = incoming.get("email")
        if incoming_email and incoming_email != target.get("email"):
            existing_emails = {target.get("email"), target.get("email2"), target.get("email3"), target.get("email4")}
            if incoming_email not in existing_emails:
                if not target.get("email2"):
                    target["email2"] = incoming_email
                elif not target.get("email3"):
                    target["email3"] = incoming_email
                elif not target.get("email4"):
                    target["email4"] = incoming_email
                target["alternate_emails"] = float(len([e for e in [target.get("email2"), target.get("email3"), target.get("email4")] if e]))

        # 6. Recompute scores to reflect enriched data
        from .data_normalizer import calculate_scores
        target.update(calculate_scores(target))
