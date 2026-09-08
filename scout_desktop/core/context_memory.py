"""
core/context_memory.py — Short-Term Context Memory & Information Gap Detection

Maintains awareness of what the Scout currently knows and doesn't know.
Provides the following cognitive capabilities:

1. Page Context Awareness:
   - Knows which page type is active (PERSON_PROFILE, COMPANY_PEOPLE, etc.)
   - Tracks which sections have been seen (About, Experience, Education, Skills)
   - Detects page navigation as a context-reset event

2. Multi-Entity Tracking:
   - Tracks multiple entities simultaneously (person + company + job)
   - Each entity maintains independent state
   - Supports identity continuity across scroll events on the same page

3. Information Gap Detection:
   - After each extraction, evaluates what critical fields are still missing
   - Generates prioritized gap lists for each tracked entity
   - Detects when a scroll might reveal missing information

4. Observation Deduplication:
   - Before staging, checks if an observation is semantically redundant
   - Prevents duplicate extraction of identical field values
   - Tracks which observations have already been staged

5. Completeness Scoring:
   - Maintains weighted completeness score per entity
   - Supports completeness tiers: MINIMAL / BASIC / GOOD / EXCELLENT
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set

logger = logging.getLogger("scout.context_memory")

# Completeness tier thresholds
COMPLETENESS_MINIMAL = 0.20
COMPLETENESS_BASIC = 0.45
COMPLETENESS_GOOD = 0.70
COMPLETENESS_EXCELLENT = 0.90

# Critical fields for recruiter/person profiles
PERSON_CRITICAL_FIELDS = {
    "identity": ["canonical_name"],
    "current_employment": ["current_title", "current_company"],
    "contact": ["email", "phone", "linkedin_url"],
    "location": ["location"],
    "education": ["education"],
    "employment_history": ["employment_history"],
    "skills": ["skills"],
    "about": ["about_summary"],
}

# Field importance weights for completeness calculation
FIELD_WEIGHTS = {
    "identity": 0.30,           # Name is the most critical
    "current_employment": 0.25, # Current role is highly valuable
    "contact": 0.20,           # Contact info is essential for outreach
    "location": 0.10,          # Geographic relevance
    "education": 0.10,         # Background context
    "skills": 0.05,            # Supplementary signals
}

# LinkedIn section names (used for section tracking)
LINKEDIN_SECTIONS = {
    "About", "Experience", "Education", "Skills", "Licenses & certifications",
    "Recommendations", "Projects", "Publications", "Languages", "Interests",
    "Volunteer experience", "Courses", "Honors & awards", "Organizations",
    "Contact info",
}


@dataclass
class EntityState:
    """
    Tracks the current knowledge state for a single entity.
    Maintains which fields are known, which are missing, and
    the overall completeness score.
    """
    entity_id: str
    entity_type: str  # PERSON | COMPANY | JOB
    canonical_name: str
    known_fields: Dict[str, Any] = field(default_factory=dict)
    known_predicates: Set[str] = field(default_factory=set)
    staged_observation_ids: Set[str] = field(default_factory=set)
    first_seen_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    source_url: str = ""
    source_capture_ids: List[str] = field(default_factory=list)

    def update_field(self, field_name: str, value: Any, predicate: str = ""):
        """Records a known field value and its predicate."""
        self.known_fields[field_name] = value
        if predicate:
            self.known_predicates.add(predicate)
        self.last_updated_at = time.time()

    def has_field(self, field_name: str) -> bool:
        """Checks if a field has been extracted."""
        return field_name in self.known_fields and self.known_fields[field_name] is not None

    def get_missing_fields(self) -> List[str]:
        """Returns a list of critical fields that haven't been extracted yet."""
        missing = []
        for category, fields in PERSON_CRITICAL_FIELDS.items():
            for f in fields:
                if not self.has_field(f):
                    missing.append(f)
        return missing

    def get_completeness_score(self) -> float:
        """
        Calculates weighted completeness score (0.0–1.0).

        Each field category contributes its weight proportionally
        based on how many fields in that category are populated.
        """
        score = 0.0
        for category, weight in FIELD_WEIGHTS.items():
            fields = PERSON_CRITICAL_FIELDS.get(category, [])
            if not fields:
                continue
            filled = sum(1 for f in fields if self.has_field(f))
            category_score = filled / len(fields)
            score += weight * category_score
        return round(score, 3)

    def get_completeness_tier(self) -> str:
        """Returns the completeness tier label."""
        score = self.get_completeness_score()
        if score >= COMPLETENESS_EXCELLENT:
            return "EXCELLENT"
        elif score >= COMPLETENESS_GOOD:
            return "GOOD"
        elif score >= COMPLETENESS_BASIC:
            return "BASIC"
        elif score >= COMPLETENESS_MINIMAL:
            return "MINIMAL"
        else:
            return "INSUFFICIENT"

    def mark_observation_staged(self, observation_id: str):
        """Records that an observation has been staged for backend sync."""
        self.staged_observation_ids.add(observation_id)

    def is_observation_staged(self, observation_id: str) -> bool:
        """Checks if an observation was already staged."""
        return observation_id in self.staged_observation_ids

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entity state for diagnostics."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "known_fields": list(self.known_fields.keys()),
            "known_predicates": list(self.known_predicates),
            "staged_count": len(self.staged_observation_ids),
            "completeness_score": self.get_completeness_score(),
            "completeness_tier": self.get_completeness_tier(),
            "missing_fields": self.get_missing_fields(),
            "age_seconds": round(time.time() - self.first_seen_at, 1),
        }


class ContextMemory:
    """
    Maintains short-term awareness of what the Scout currently knows.

    This is the central intelligence module that prevents redundant extraction,
    enables profile continuity across scrolls, and drives information gap detection.

    Usage:
        memory = ContextMemory()

        # On page navigation
        memory.update_page_context("PERSON_PROFILE", "https://linkedin.com/in/john-doe")

        # On entity extraction
        memory.register_entity("ENT-12345", "PERSON", "John Doe")
        memory.update_entity_field("ENT-12345", "current_title", "Senior Recruiter", "HAS_TITLE")

        # Before staging
        if not memory.is_redundant_observation(obs):
            stage(obs)

        # Check gaps
        gaps = memory.get_information_gaps("ENT-12345")
        # → ["email", "phone", "education", "employment_history"]
    """

    # Context expiry: if no updates for this long, clear context
    CONTEXT_EXPIRY_SEC = 300.0  # 5 minutes

    def __init__(self, ttl_sec: Optional[float] = None):
        self.context_expiry_sec = ttl_sec if ttl_sec is not None else self.CONTEXT_EXPIRY_SEC
        # Page-level context
        self.active_page_type: str = "UNKNOWN"
        self.active_url: str = ""
        self.active_platform: str = "UNKNOWN"
        self.seen_sections: Set[str] = set()
        self.page_context_updated_at: float = time.time()

        # Entity tracking
        self._entities: Dict[str, EntityState] = {}
        self._primary_entity_id: Optional[str] = None

        # Deduplication tracking
        self._seen_field_hashes: Set[str] = set()  # "entity_id:field:value" hashes

        # Telemetry
        self._stats = {
            "total_entities_tracked": 0,
            "total_observations_deduplicated": 0,
            "total_context_resets": 0,
            "total_gap_evaluations": 0,
        }

        logger.info("ContextMemory initialized")

    def compute_completeness(self, entity_id: str) -> float:
        """Computes completeness score (0.0–1.0) for a tracked entity."""
        ent = self._entities.get(entity_id)
        return ent.get_completeness_score() if ent else 0.0

    def get_entity_dict(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Returns standard dict representation of a tracked entity for resolver."""
        ent = self._entities.get(entity_id)
        if not ent:
            return None
        d = dict(ent.known_fields)
        d["entity_id"] = ent.entity_id
        d["canonical_name"] = ent.canonical_name
        d["entity_type"] = ent.entity_type
        d["source_url"] = ent.source_url
        return d

    # ─── Page Context Management ──────────────────────────────────

    def update_page_context(self, page_type: str, url: str, platform: str = "UNKNOWN"):
        """
        Updates the active page context. If the URL has changed significantly,
        triggers a context reset to avoid cross-page contamination.

        Args:
            page_type: The classified page type (PERSON_PROFILE, COMPANY_PEOPLE, etc.)
            url: The current page URL.
            platform: The detected platform (LINKEDIN, INDEED, etc.)
        """
        url_changed = self._is_significant_url_change(self.active_url, url)

        if url_changed:
            logger.info(
                "Page context changed: %s → %s (%s → %s)",
                self.active_page_type, page_type,
                self._url_summary(self.active_url), self._url_summary(url)
            )
            self.reset_on_navigation()

        self.active_page_type = page_type
        self.active_url = url
        self.active_platform = platform
        self.page_context_updated_at = time.time()

    def mark_section_seen(self, section_name: str):
        """Records that a page section (e.g., 'Experience', 'Education') has been seen."""
        if section_name not in self.seen_sections:
            self.seen_sections.add(section_name)
            logger.debug("Section seen: %s (total: %d)", section_name, len(self.seen_sections))

    def get_unseen_sections(self) -> List[str]:
        """Returns LinkedIn sections that haven't been scrolled past yet."""
        return sorted(LINKEDIN_SECTIONS - self.seen_sections)

    # ─── Entity Registration & Tracking ──────────────────────────

    def register_entity(
        self,
        entity_id: str,
        entity_type: str,
        canonical_name: str,
        source_url: str = "",
        capture_id: str = "",
    ) -> EntityState:
        """
        Registers a new entity or retrieves an existing one by ID.

        If the entity already exists, enriches it with the new capture context.
        If it's new, creates a fresh EntityState.

        Args:
            entity_id: Unique entity identifier.
            entity_type: PERSON | COMPANY | JOB.
            canonical_name: Human-readable name.
            source_url: The URL where this entity was observed.
            capture_id: The capture frame ID.

        Returns:
            The EntityState (existing or newly created).
        """
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            if capture_id and capture_id not in entity.source_capture_ids:
                entity.source_capture_ids.append(capture_id)
            entity.last_updated_at = time.time()
            return entity

        entity = EntityState(
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
            source_url=source_url,
            source_capture_ids=[capture_id] if capture_id else [],
        )
        self._entities[entity_id] = entity
        self._stats["total_entities_tracked"] += 1

        # First person entity becomes the primary
        if entity_type == "PERSON" and self._primary_entity_id is None:
            self._primary_entity_id = entity_id

        logger.info(
            "Entity registered: %s [%s] '%s' (total: %d)",
            entity_id, entity_type, canonical_name, len(self._entities)
        )
        return entity

    def find_entity_by_name(self, name: str, entity_type: str = "PERSON") -> Optional[EntityState]:
        """
        Finds an existing entity by name and type.
        Used for profile continuity — if we've already seen "John Doe",
        we want to enrich the same entity rather than create a duplicate.

        Args:
            name: The canonical name to search for.
            entity_type: The entity type to filter by.

        Returns:
            EntityState if found, None otherwise.
        """
        name_lower = name.strip().lower()
        for entity in self._entities.values():
            if (entity.entity_type == entity_type
                    and entity.canonical_name.strip().lower() == name_lower):
                return entity
        return None

    def get_primary_entity(self) -> Optional[EntityState]:
        """Returns the primary tracked entity (usually the person on a profile page)."""
        if self._primary_entity_id and self._primary_entity_id in self._entities:
            return self._entities[self._primary_entity_id]
        return None

    def get_all_entities(self, entity_type: Optional[str] = None) -> List[EntityState]:
        """Returns all tracked entities, optionally filtered by type."""
        if entity_type:
            return [e for e in self._entities.values() if e.entity_type == entity_type]
        return list(self._entities.values())

    # ─── Field Updates & Gap Detection ────────────────────────────

    def update_entity_field(
        self,
        entity_id: str,
        field_name: str,
        value: Any,
        predicate: str = "",
    ) -> bool:
        """
        Updates a field on a tracked entity.

        Returns True if this is a NEW field value (not redundant).
        Returns False if the field already has this exact value (redundant).

        Args:
            entity_id: The entity to update.
            field_name: The field name (e.g., 'current_title', 'email').
            value: The extracted value.
            predicate: The observation predicate (e.g., 'HAS_TITLE').

        Returns:
            True if the value is new/different, False if redundant.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            logger.warning("Cannot update field on unknown entity: %s", entity_id)
            return False

        # Check for redundancy
        field_hash = f"{entity_id}:{field_name}:{str(value).strip().lower()}"
        if field_hash in self._seen_field_hashes:
            self._stats["total_observations_deduplicated"] += 1
            return False

        self._seen_field_hashes.add(field_hash)
        entity.update_field(field_name, value, predicate)
        return True

    def get_information_gaps(self, entity_id: str) -> List[str]:
        """
        Returns a prioritized list of missing critical fields for an entity.

        Higher-weight fields appear first. This drives the intelligence
        router to escalate to Level 3 (RESOLVE) when gaps exist.

        Args:
            entity_id: The entity to evaluate.

        Returns:
            List of missing field names, ordered by importance.
        """
        self._stats["total_gap_evaluations"] += 1

        entity = self._entities.get(entity_id)
        if not entity:
            return []

        missing = entity.get_missing_fields()

        # Sort by field weight (most important first)
        weight_map = {}
        for category, fields in PERSON_CRITICAL_FIELDS.items():
            w = FIELD_WEIGHTS.get(category, 0.0)
            for f in fields:
                weight_map[f] = w

        missing.sort(key=lambda f: weight_map.get(f, 0.0), reverse=True)
        return missing

    def has_pending_gaps(self, entity_id: Optional[str] = None) -> bool:
        """
        Checks if any tracked entity has important information gaps.

        If entity_id is None, checks the primary entity.
        """
        if entity_id is None:
            entity_id = self._primary_entity_id
        if not entity_id:
            return False

        entity = self._entities.get(entity_id)
        if not entity:
            return False

        # Consider a gap significant if completeness is below GOOD
        return entity.get_completeness_score() < COMPLETENESS_GOOD

    # ─── Observation Deduplication ────────────────────────────────

    def is_redundant_observation(self, entity_id: str, predicate: str, value: Any) -> bool:
        """
        Checks if an observation is semantically redundant.

        An observation is redundant if the same entity already has the same
        predicate-value combination tracked in context memory.

        Args:
            entity_id: The target entity.
            predicate: The observation predicate (e.g., 'HAS_TITLE').
            value: The observation value.

        Returns:
            True if this observation is redundant and should be skipped.
        """
        field_hash = f"{entity_id}:{predicate}:{str(value).strip().lower()}"
        if field_hash in self._seen_field_hashes:
            self._stats["total_observations_deduplicated"] += 1
            return True
        return False

    def should_process_frame(self, page_url: str, visual_delta: float) -> bool:
        """
        Quick check: should this frame be sent for extraction?

        Returns False if:
        - We're on the same URL with no visual change.
        - Context has expired (stale data).
        - All entities on this page are already at EXCELLENT completeness.

        Returns True if:
        - URL changed, visual change detected, or gaps exist.
        """
        # Context expiry check
        if time.time() - self.page_context_updated_at > self.CONTEXT_EXPIRY_SEC:
            return True  # Stale context → refresh

        # Visual change → always process
        if visual_delta >= 0.035:
            return True

        # Check if any entity has gaps
        for entity in self._entities.values():
            if entity.get_completeness_score() < COMPLETENESS_EXCELLENT:
                return True

        return False

    # ─── Context Reset & Lifecycle ────────────────────────────────

    def reset_on_navigation(self):
        """
        Clears context when the user navigates to a different page.

        This prevents cross-page contamination (e.g., attributing Company B's
        employee to Company A's profile because context wasn't cleared).

        Note: Does NOT clear staged observation tracking — those are permanent
        for the session to prevent re-staging.
        """
        entity_count = len(self._entities)
        if entity_count > 0:
            logger.info(
                "Context reset: clearing %d entities, %d sections, %d field hashes",
                entity_count, len(self.seen_sections), len(self._seen_field_hashes)
            )

        self._entities.clear()
        self._primary_entity_id = None
        self.seen_sections.clear()
        self._seen_field_hashes.clear()
        self._stats["total_context_resets"] += 1

    def expire_stale_entities(self, max_age_sec: float = 300.0):
        """Removes entities that haven't been updated in max_age_sec."""
        now = time.time()
        stale_ids = [
            eid for eid, entity in self._entities.items()
            if (now - entity.last_updated_at) > max_age_sec
        ]
        for eid in stale_ids:
            entity = self._entities.pop(eid)
            logger.debug("Expired stale entity: %s '%s'", eid, entity.canonical_name)
            if eid == self._primary_entity_id:
                self._primary_entity_id = None

    # ─── Diagnostics & Telemetry ──────────────────────────────────

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive context memory telemetry."""
        entities_summary = []
        for entity in self._entities.values():
            entities_summary.append(entity.to_dict())

        return {
            "active_page_type": self.active_page_type,
            "active_url": self.active_url,
            "active_platform": self.active_platform,
            "seen_sections": sorted(self.seen_sections),
            "unseen_sections": self.get_unseen_sections(),
            "tracked_entities": entities_summary,
            "tracked_entity_count": len(self._entities),
            "primary_entity_id": self._primary_entity_id,
            "stats": dict(self._stats),
        }

    # ─── Internal Helpers ─────────────────────────────────────────

    @staticmethod
    def _is_significant_url_change(old_url: str, new_url: str) -> bool:
        """
        Determines if a URL change is significant enough to trigger context reset.

        Same-page anchors (#section) and query parameter changes on the same path
        are NOT considered significant. Different paths ARE significant.
        """
        if not old_url or not new_url:
            return True

        try:
            from urllib.parse import urlparse
            old_parsed = urlparse(old_url)
            new_parsed = urlparse(new_url)

            # Different domain → definitely significant
            if old_parsed.netloc != new_parsed.netloc:
                return True

            # Different path → significant
            if old_parsed.path.rstrip("/") != new_parsed.path.rstrip("/"):
                return True

            # Same path, different query/fragment → not significant (same profile, different tab)
            return False

        except Exception:
            # If parsing fails, assume significant
            return old_url != new_url

    @staticmethod
    def _url_summary(url: str) -> str:
        """Returns a short summary of a URL for logging."""
        if not url:
            return "(none)"
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            if len(path) > 40:
                path = path[:37] + "..."
            return f"{parsed.netloc}{path}"
        except Exception:
            return url[:50]
