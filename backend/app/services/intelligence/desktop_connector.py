"""
desktop_connector.py — Adapter for TalentOps Scout Desktop into the Universal Ingestion Gateway.

Translates candidate extractions, visual frames, and OCR captures from the Desktop Companion
into canonical UniversalSourceObject contracts with hardware provenance.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from ...schemas.intelligence_contracts import (
    UniversalSourceObject,
    SourceObjectIdentity,
    SourceType,
    ScopeLevel,
)


def wrap_desktop_observation(
    staged_contact: Dict[str, Any],
    device_id: str = "DESKTOP-SCOUT-WIN",
    hostname: str = "WORKSTATION",
    scout_version: str = "2.0.0",
) -> UniversalSourceObject:
    """
    Converts a Scout Desktop staged contact payload into a UniversalSourceObject.
    """
    cand_name = staged_contact.get("recruiter_name") or staged_contact.get("raw_name") or "Unknown"
    comp_name = staged_contact.get("company_name") or staged_contact.get("raw_company") or ""
    linkedin = staged_contact.get("linkedin_url") or staged_contact.get("raw_linkedin") or ""
    capture_id = staged_contact.get("capture_id") or "VC-MANUAL"

    # Deterministic content hash from candidate core signals
    core_tuple = (
        cand_name.strip().lower(),
        comp_name.strip().lower(),
        linkedin.strip().lower(),
    )
    content_hash = hashlib.sha256(":".join(core_tuple).encode("utf-8")).hexdigest()

    identity = SourceObjectIdentity(
        source=SourceType.SCOUT_DESKTOP,
        source_object_type="person",
        source_object_id=f"SCOUT-{capture_id}",
        authorization_scope=ScopeLevel.DESKTOP_OBSERVATION.value,
        content_hash=content_hash,
    )

    provenance = {
        "device_id": device_id,
        "hostname": hostname,
        "scout_version": scout_version,
        "capture_id": capture_id,
        "source_url": staged_contact.get("source_url"),
        "visual_change_score": staged_contact.get("visual_change_score"),
        "ingest_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Normalized payload matching PersonFact schema expectations
    payload = {
        "full_name": cand_name,
        "current_title": staged_contact.get("title") or staged_contact.get("raw_title"),
        "company_name": comp_name,
        "primary_email": staged_contact.get("email") or staged_contact.get("raw_email"),
        "primary_phone": staged_contact.get("phone") or staged_contact.get("raw_phone"),
        "linkedin_url": linkedin,
        "location": staged_contact.get("location") or staged_contact.get("raw_location"),
        "seniority_level": staged_contact.get("seniority_level"),
        "observations_count": staged_contact.get("observations_count", 1),
    }

    return UniversalSourceObject(
        identity=identity,
        raw_payload=payload,
        provenance_metadata=provenance,
    )
