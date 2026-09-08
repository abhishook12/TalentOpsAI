"""
extractor/identity_resolver.py — Client-Side Entity Resolution Engine

Resolves whether a newly extracted entity matches an existing known entity,
using a hierarchical evidence scoring system:

1. STRONG signals (LinkedIn URL, verified email, phone) → auto-match
2. MODERATE signals (name + company, name + location, name + title) → likely match
3. WEAK signals (name only, first name, generic title) → require more evidence

Also handles:
- Field-level enrichment merging (adding new fields to existing entities)
- Conflict detection (two different values for the same field)
- Historical vs current data protection (never replace current company with past employer)
"""

from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger("scout.identity_resolver")

@dataclass
class Conflict:
    """Represents a conflict between an existing field value and a newly extracted one."""
    field_name: str
    existing_value: str
    new_value: str
    resolution: str  # KEEP_EXISTING | UPDATE | TIMELINE_CHANGE | OCR_ERROR | DIFFERENT_PERSON
    confidence: float

@dataclass
class ResolutionResult:
    """Result of attempting to resolve a new entity against known entities."""
    outcome: str  # SAME_ENTITY | NEW_ENTITY | REVIEW_REQUIRED
    confidence: float
    matched_entity_id: Optional[str]
    match_signals: list[str]
    conflicts: list[Conflict] = field(default_factory=list)

class IdentityResolver:
    """
    Client-side entity resolution engine for matching new extractions
    to existing known entities using hierarchical evidence scoring.
    """
    
    STRONG_SIGNALS = {"linkedin_url": 0.95, "email": 0.90, "phone": 0.85}
    MODERATE_SIGNALS = {"name_company": 0.70, "name_location": 0.60, "name_title": 0.55}
    WEAK_SIGNALS = {"name_only": 0.30, "first_name": 0.15}
    
    MATCH_THRESHOLD = 0.65
    REVIEW_THRESHOLD = 0.40

    def __init__(self):
        """Initialize the IdentityResolver and its statistics counters."""
        self.total_resolved = 0
        self.matches_found = 0
        self.reviews_required = 0
        self.new_entities = 0

    def resolve(self, new_entity_data: dict, known_entities: list[dict]) -> ResolutionResult:
        """
        Score each known entity against the new entity by checking available signals.
        Returns the best match or NEW_ENTITY if no satisfactory match is found.
        """
        best_score = 0.0
        best_match_id = None
        best_signals = []
        best_entity = None
        
        for known in known_entities:
            score = 0.0
            signals = []
            
            # 1. STRONG SIGNALS
            if new_entity_data.get('linkedin_url') and known.get('linkedin_url'):
                if self._normalize_url(new_entity_data['linkedin_url']) == self._normalize_url(known['linkedin_url']):
                    score += self.STRONG_SIGNALS["linkedin_url"]
                    signals.append("linkedin_url")
                    
            if new_entity_data.get('email') and known.get('email'):
                if str(new_entity_data['email']).lower().strip() == str(known['email']).lower().strip():
                    score += self.STRONG_SIGNALS["email"]
                    signals.append("email")
                    
            if new_entity_data.get('phone') and known.get('phone'):
                p1 = re.sub(r'\D', '', str(new_entity_data['phone']))
                p2 = re.sub(r'\D', '', str(known['phone']))
                if p1 and p2 and p1 == p2:
                    score += self.STRONG_SIGNALS["phone"]
                    signals.append("phone")
                    
            # 2. MODERATE / WEAK SIGNALS (require name match)
            name_score = 0.0
            if new_entity_data.get('canonical_name') and known.get('canonical_name'):
                name_score = self._compute_name_similarity(new_entity_data['canonical_name'], known['canonical_name'])
                
            if name_score > 0.8:  # Good name match
                if new_entity_data.get('current_company') and known.get('current_company'):
                    if str(new_entity_data['current_company']).lower().strip() == str(known['current_company']).lower().strip():
                        score += self.MODERATE_SIGNALS["name_company"]
                        signals.append("name_company")
                elif new_entity_data.get('location') and known.get('location'):
                    if str(new_entity_data['location']).lower().strip() == str(known['location']).lower().strip():
                        score += self.MODERATE_SIGNALS["name_location"]
                        signals.append("name_location")
                elif new_entity_data.get('current_title') and known.get('current_title'):
                    if str(new_entity_data['current_title']).lower().strip() == str(known['current_title']).lower().strip():
                        score += self.MODERATE_SIGNALS["name_title"]
                        signals.append("name_title")
                else:
                    score += self.WEAK_SIGNALS["name_only"]
                    signals.append("name_only")
            elif name_score > 0.4: # Partial name match (e.g. first name only)
                 score += self.WEAK_SIGNALS["first_name"]
                 signals.append("first_name")
                    
            if score > best_score:
                best_score = score
                best_match_id = known.get('entity_id') or known.get('id')
                best_signals = signals
                best_entity = known
                
        # Determine outcome
        outcome = "NEW_ENTITY"
        conflicts = []
        
        self.total_resolved += 1
        
        if best_score >= self.MATCH_THRESHOLD:
            outcome = "SAME_ENTITY"
            self.matches_found += 1
            if best_entity:
                conflicts = self.detect_conflicts(best_entity, new_entity_data)
        elif best_score >= self.REVIEW_THRESHOLD:
            outcome = "REVIEW_REQUIRED"
            self.reviews_required += 1
        else:
            self.new_entities += 1
            
        return ResolutionResult(
            outcome=outcome,
            confidence=min(best_score, 1.0),
            matched_entity_id=best_match_id if outcome != "NEW_ENTITY" else None,
            match_signals=best_signals,
            conflicts=conflicts
        )

    def merge_entities(self, primary: dict, secondary: dict) -> dict:
        """
        Merge fields from secondary into primary where primary has None/empty.
        Never overwrites existing non-None fields in primary.
        """
        merged = primary.copy()
        for k, v in secondary.items():
            if not merged.get(k) and v:
                merged[k] = v
        return merged

    def detect_conflicts(self, existing: dict, new_data: dict) -> list[Conflict]:
        """
        Compare field values between existing and new data to find and classify conflicts.
        """
        conflicts = []
        for k, new_v in new_data.items():
            if not new_v:
                continue
            existing_v = existing.get(k)
            if not existing_v:
                continue
                
            if str(existing_v).strip().lower() != str(new_v).strip().lower():
                resolution = "UPDATE"
                confidence = 0.5
                
                # Timeline change check
                if k == 'current_company':
                    hist = existing.get('employment_history', [])
                    if isinstance(hist, list) and any(str(new_v).lower() in str(h).lower() for h in hist):
                        resolution = "TIMELINE_CHANGE"
                        confidence = 0.9
                
                # OCR error check
                if isinstance(existing_v, str) and isinstance(new_v, str):
                    if self._levenshtein(str(existing_v).lower(), str(new_v).lower()) <= 2:
                        resolution = "OCR_ERROR"
                        confidence = 0.8
                
                conflicts.append(Conflict(
                    field_name=k,
                    existing_value=str(existing_v),
                    new_value=str(new_v),
                    resolution=resolution,
                    confidence=confidence
                ))
                
        return conflicts

    def _normalize_name(self, name: str) -> str:
        """Lowercase, strip, remove special chars from name."""
        name = str(name).lower().strip()
        return re.sub(r'[^a-z\s]', '', name)

    def _normalize_url(self, url: str) -> str:
        """Lowercase, strip trailing slashes, remove query params."""
        url = str(url).lower().strip()
        url = url.split('?')[0]
        return url.rstrip('/')

    def _compute_name_similarity(self, name1: str, name2: str) -> float:
        """Simple token-based fuzzy match for names."""
        n1_tokens = set(self._normalize_name(name1).split())
        n2_tokens = set(self._normalize_name(name2).split())
        
        if not n1_tokens or not n2_tokens:
            return 0.0
            
        intersection = n1_tokens.intersection(n2_tokens)
        union = n1_tokens.union(n2_tokens)
        
        return len(intersection) / len(union) if union else 0.0

    def _levenshtein(self, s1: str, s2: str) -> int:
        """Compute the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
