"""
TalentOps Scout 2.0 - Intelligent Delta & Change Detection Engine
Maintains edge entity cache, performs field-level diffs, and computes
priority-ranked deltas so only actionable intelligence is synced.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("scout.change_detector")


class ChangeOperation(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    IGNORE = "IGNORE"


class DeltaPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IGNORE = "IGNORE"


@dataclass
class ChangeResult:
    operation: ChangeOperation
    priority: DeltaPriority
    entity_id: str
    changed_fields: list[str]
    delta: dict[str, Any]
    content_hash: str
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation.value,
            "priority": self.priority.value,
            "entity_id": self.entity_id,
            "changed_fields": self.changed_fields,
            "delta": self.delta,
            "content_hash": self.content_hash,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class ChangeDetector:
    """
    Evaluates new entity observations against locally cached knowledge.
    Computes field-level deltas, avoids redundant uploads (IGNORE), and
    assigns queue priority (HIGH/MEDIUM/LOW).
    """

    # Canonical facts that can create real value downstream.  They are kept
    # source-neutral so LinkedIn, Dice, SimplyHired, and direct UIA captures
    # all produce the same semantic delta.
    RELEVANT_FIELDS = [
        "name", "title", "company", "location", "email", "phone",
        "linkedin_url", "education", "skills", "experience_history",
        "about_summary", "entity_type", "page_type",
    ]

    @classmethod
    def normalize_entity(cls, entity_data: dict[str, Any]) -> dict[str, Any]:
        """Convert source-specific field aliases into one comparable profile."""
        return {
            "name": entity_data.get("name") or entity_data.get("canonical_name") or entity_data.get("recruiter_name") or "",
            "title": entity_data.get("title") or entity_data.get("current_title") or entity_data.get("raw_title") or "",
            "company": entity_data.get("company") or entity_data.get("company_name") or entity_data.get("current_company") or entity_data.get("raw_company") or "",
            "location": entity_data.get("location") or entity_data.get("raw_location") or "",
            "email": entity_data.get("email") or entity_data.get("primary_email") or entity_data.get("raw_email") or "",
            "phone": entity_data.get("phone") or entity_data.get("primary_phone") or entity_data.get("raw_phone") or "",
            "linkedin_url": entity_data.get("linkedin_url") or entity_data.get("canonical_profile_url") or entity_data.get("raw_linkedin") or "",
            "education": entity_data.get("education") or "",
            "skills": entity_data.get("skills") or [],
            "experience_history": entity_data.get("experience_history") or [],
            "about_summary": entity_data.get("about_summary") or "",
            "entity_type": entity_data.get("entity_type") or "PERSON",
            "page_type": entity_data.get("page_type") or "",
        }

    def __init__(self, cache_file_path: Optional[str] = None) -> None:
        self.cache_file_path = cache_file_path
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load known entities cache from disk if available."""
        if not self.cache_file_path or not os.path.exists(self.cache_file_path):
            return

        try:
            with open(self.cache_file_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info("Loaded %d entities into local delta cache", len(self._cache))
        except Exception as e:
            logger.warning("Could not read delta cache file: %s", e)
            self._cache = {}

    def save_cache(self) -> None:
        """Persist cache to disk."""
        if not self.cache_file_path:
            return

        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.cache_file_path)), exist_ok=True)
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save delta cache: %s", e)

    @classmethod
    def compute_content_hash(cls, entity_data: dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash across relevant semantic fields."""
        normalized = cls.normalize_entity(entity_data)
        subset = {k: normalized.get(k, "") for k in cls.RELEVANT_FIELDS}
        # Sort lists if any (e.g. skills)
        if isinstance(subset.get("skills"), list):
            subset["skills"] = sorted([str(s) for s in subset["skills"]])
        serialized = json.dumps(subset, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def derive_entity_id(cls, entity_data: dict[str, Any]) -> str:
        """Extract canonical identity key from entity data."""
        slug = entity_data.get("slug") or entity_data.get("linkedin_url") or entity_data.get("canonical_id")
        if slug:
            # Normalize slug
            clean_slug = str(slug).split("?")[0].rstrip("/").split("/")[-1].lower()
            return f"linkedin:{clean_slug}"

        email = entity_data.get("email")
        if email and "@" in email and not email.endswith("talentops.ai"):
            return f"email:{email.strip().lower()}"

        name = entity_data.get("name") or entity_data.get("canonical_name") or entity_data.get("recruiter_name") or "unknown"
        company = entity_data.get("company") or entity_data.get("company_name") or "unknown"
        return f"name_co:{name.strip().lower()}_{company.strip().lower()}"

    def evaluate_entity(self, entity_data: dict[str, Any]) -> ChangeResult:
        """
        Evaluate observation against local state:
        - INSERT if new entity
        - IGNORE if identical content hash
        - UPDATE with delta and priority if content differs
        """
        normalized = self.normalize_entity(entity_data)
        entity_id = self.derive_entity_id(normalized)
        current_hash = self.compute_content_hash(normalized)

        # 1. Check if entity is already known
        cached = self._cache.get(entity_id)
        if not cached:
            # Brand new entity -> INSERT, HIGH priority
            self._cache[entity_id] = {
                "hash": current_hash,
                "data": copy.deepcopy(normalized),
                "last_seen": time.time(),
                "observation_count": 1,
            }
            self.save_cache()
            return ChangeResult(
                operation=ChangeOperation.INSERT,
                priority=DeltaPriority.HIGH,
                entity_id=entity_id,
                changed_fields=[],
                delta=normalized,
                content_hash=current_hash,
                reason="New entity discovered on edge",
            )

        # 2. Check if identical content hash
        if cached.get("hash") == current_hash:
            # No changes -> IGNORE (zero-bandwidth delta)
            cached["last_seen"] = time.time()
            cached["observation_count"] = cached.get("observation_count", 1) + 1
            return ChangeResult(
                operation=ChangeOperation.IGNORE,
                priority=DeltaPriority.IGNORE,
                entity_id=entity_id,
                changed_fields=[],
                delta={},
                content_hash=current_hash,
                reason="Identical observation hash: zero changes",
            )

        # 3. Content changed -> compute field-level delta
        old_data = self.normalize_entity(cached.get("data", {}))
        changed_fields: list[str] = []
        delta: dict[str, Any] = {}

        for key in self.RELEVANT_FIELDS:
            old_val = old_data.get(key)
            new_val = normalized.get(key)
            if old_val != new_val:
                changed_fields.append(key)
                delta[key] = {
                    "old": old_val,
                    "new": new_val,
                }

        # Determine priority based on business impact
        priority = DeltaPriority.LOW
        reason = "Minor profile field update"

        if "company" in changed_fields or "title" in changed_fields or "experience_history" in changed_fields:
            priority = DeltaPriority.HIGH
            reason = "Critical career move or role promotion detected"
        elif any(field in changed_fields for field in ("email", "phone", "skills", "education", "about_summary")):
            priority = DeltaPriority.MEDIUM
            reason = "Valuable contact or skills intelligence enrichment"

        # Update cache
        cached["hash"] = current_hash
        cached["data"] = copy.deepcopy(normalized)
        cached["last_seen"] = time.time()
        cached["observation_count"] = cached.get("observation_count", 1) + 1
        self.save_cache()

        return ChangeResult(
            operation=ChangeOperation.UPDATE,
            priority=priority,
            entity_id=entity_id,
            changed_fields=changed_fields,
            delta=delta,
            content_hash=current_hash,
            reason=reason,
        )

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "cached_entities_count": len(self._cache),
            "cache_file": self.cache_file_path,
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self.save_cache()
