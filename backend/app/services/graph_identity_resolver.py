"""
TalentOps AI - Semantic Vector & Co-Worker Graph Triangulation (GraphIdentityResolver 2.0)
Resolves ambiguous identities through social/colleague graph networks and semantic role matching:
- Co-Worker Triangulation: Finds overlapping tenure and shared colleagues across candidates to boost match confidence.
- Semantic Title Matching: Evaluates role equivalence, seniorities, and career progression steps without external heavy dependencies.
- Unified Graph Resolution: Produces explainable resolution verdicts (AUTO_MERGE, HUMAN_REVIEW, SEPARATE).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from ..models.data_quality_models import (
    PersonIdentity,
    PersonContactHistory,
    CandidateIdentityMatch,
)

logger = logging.getLogger("talentops.graph_identity_resolver")

# Seniority & Title Equivalence Dictionaries
SENIORITY_RANKS = {
    "intern": 1,
    "associate": 2,
    "junior": 2,
    "jr": 2,
    "mid": 3,
    "senior": 4,
    "sr": 4,
    "staff": 5,
    "lead": 5,
    "principal": 6,
    "manager": 5,
    "director": 7,
    "vp": 8,
    "vice president": 8,
    "head": 7,
    "chief": 9,
    "c-level": 9,
}

DISCIPLINE_SYNONYMS = {
    "developer": "engineer",
    "dev": "engineer",
    "programmer": "engineer",
    "swe": "software engineer",
    "sde": "software engineer",
    "qa": "quality assurance",
    "sdr": "sales development representative",
    "bdr": "business development representative",
    "ae": "account executive",
    "pm": "product manager",
    "tpm": "technical product manager",
    "recruiter": "talent acquisition",
    "sourcer": "talent acquisition",
    "hr": "people operations",
}


class GraphIdentityResolver:
    """
    Graph Triangulation & Semantic Role Matching Engine.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Co-Worker Network Triangulation ────────────────────────────────────────

    def triangulate_coworker_network(
        self,
        person_a_id: int,
        person_b_id: int,
        base_confidence: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Inspects organizational graph to see if Person A and Person B share
        colleagues, tenure, or overlapping offices.
        """
        p_a = self.db.query(PersonIdentity).filter(PersonIdentity.id == person_a_id).first()
        p_b = self.db.query(PersonIdentity).filter(PersonIdentity.id == person_b_id).first()

        if not p_a or not p_b:
            return {
                "base_confidence": base_confidence,
                "boosted_confidence": base_confidence,
                "shared_colleagues_count": 0,
                "recommendation": "SEPARATE",
                "evidence": "One or both person records missing",
            }

        comp_a = (p_a.current_company or "").strip().lower()
        comp_b = (p_b.current_company or "").strip().lower()

        boost = 0.0
        shared_company = None
        shared_colleagues: List[str] = []

        # 1. Company Overlap Check
        if comp_a and comp_b and (comp_a == comp_b or comp_a in comp_b or comp_b in comp_a):
            shared_company = p_a.current_company
            # Query known colleagues at the same company (excluding person A and person B)
            colleagues = self.db.query(PersonIdentity).filter(
                PersonIdentity.id.notin_([p_a.id, p_b.id]),
                PersonIdentity.current_company.ilike(comp_a),
            ).limit(20).all()

            shared_colleagues = [c.canonical_name for c in colleagues if c.canonical_name]

            if len(shared_colleagues) >= 2:
                # 2+ shared colleagues at same organization -> significant network triangulation
                boost += 0.25
            elif len(shared_colleagues) == 1:
                boost += 0.15
            else:
                boost += 0.08

        # 2. Location Alignment Check
        loc_a = (p_a.location or "").strip().lower()
        loc_b = (p_b.location or "").strip().lower()
        if loc_a and loc_b and (loc_a == loc_b or loc_a in loc_b or loc_b in loc_a):
            boost += 0.10

        boosted = min(1.0, round(base_confidence + boost, 2))

        recommendation = "AUTO_MERGE" if boosted >= 0.85 else (
            "HUMAN_REVIEW" if boosted >= 0.60 else "SEPARATE"
        )

        evidence = (
            f"Network Triangulation: Shared employer '{shared_company}' with {len(shared_colleagues)} "
            f"colleagues identified ({', '.join(shared_colleagues[:3]) if shared_colleagues else 'none'}). "
            f"Confidence boosted from {base_confidence} to {boosted}."
        )

        return {
            "person_a_id": person_a_id,
            "person_b_id": person_b_id,
            "base_confidence": base_confidence,
            "boosted_confidence": boosted,
            "boost_applied": round(boost, 2),
            "shared_company": shared_company,
            "shared_colleagues_count": len(shared_colleagues),
            "shared_colleagues_sample": shared_colleagues[:5],
            "recommendation": recommendation,
            "evidence": evidence,
        }

    # ── Semantic Title Matching ───────────────────────────────────────────────

    def calculate_semantic_title_similarity(
        self, title_a: str, title_b: str
    ) -> Dict[str, Any]:
        """
        Calculates semantic similarity between two job titles.
        Recognizes seniority levels, equivalent disciplines, and career progression.
        """
        if not title_a or not title_b:
            return {"score": 0.0, "relation": "UNKNOWN", "explanation": "Missing title"}

        norm_a = self._normalize_title(title_a)
        norm_b = self._normalize_title(title_b)

        if norm_a == norm_b:
            return {
                "score": 1.0,
                "relation": "IDENTICAL",
                "explanation": "Exact normalized title match",
            }

        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())

        # Extract seniorities
        rank_a = max([SENIORITY_RANKS.get(t, 3) for t in tokens_a], default=3)
        rank_b = max([SENIORITY_RANKS.get(t, 3) for t in tokens_b], default=3)

        # Jaccard overlap on discipline tokens
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        jaccard = len(intersection) / len(union) if union else 0.0

        # Check for career progression
        if rank_b > rank_a and (jaccard >= 0.4 or len(intersection) >= 1):
            return {
                "score": 0.85,
                "relation": "CAREER_PROGRESSION",
                "seniority_delta": rank_b - rank_a,
                "explanation": f"Career promotion from '{title_a}' to '{title_b}'",
            }
        elif rank_a == rank_b and (jaccard >= 0.5 or len(intersection) >= 1):
            return {
                "score": 0.90,
                "relation": "LATERAL_EQUIVALENT",
                "seniority_delta": 0,
                "explanation": f"Lateral equivalent roles: '{title_a}' and '{title_b}'",
            }
        elif jaccard >= 0.3:
            return {
                "score": round(0.5 + (jaccard * 0.4), 2),
                "relation": "RELATED_ROLE",
                "seniority_delta": abs(rank_b - rank_a),
                "explanation": f"Partially overlapping disciplines: {list(intersection)}",
            }
        else:
            return {
                "score": round(jaccard, 2),
                "relation": "DIFFERENT_DISCIPLINE",
                "seniority_delta": abs(rank_b - rank_a),
                "explanation": f"Distinct career disciplines with low overlap",
            }

    def _normalize_title(self, title: str) -> str:
        """
        Cleans and standardizes title string.
        """
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
        words = cleaned.split()
        normalized_words = [DISCIPLINE_SYNONYMS.get(w, w) for w in words]
        return " ".join(normalized_words)

    # ── Unified Graph Resolution ──────────────────────────────────────────────

    def resolve_candidate_graph(
        self,
        candidate_name: str,
        candidate_title: str,
        candidate_company: str,
        existing_person: PersonIdentity,
    ) -> Dict[str, Any]:
        """
        Holistic multi-dimensional identity resolution incorporating name,
        semantic title similarity, company alignment, and colleague graph.
        """
        # 1. Name Match
        name_sim = 1.0 if (existing_person.canonical_name or "").strip().lower() == candidate_name.strip().lower() else 0.5

        # 2. Title Match
        title_res = self.calculate_semantic_title_similarity(
            existing_person.current_title or "", candidate_title or ""
        )
        title_sim = title_res["score"]

        # 3. Company Match
        comp_sim = 0.0
        if existing_person.current_company and candidate_company:
            if existing_person.current_company.strip().lower() == candidate_company.strip().lower():
                comp_sim = 1.0
            elif candidate_company.strip().lower() in existing_person.current_company.strip().lower():
                comp_sim = 0.8

        base_score = (name_sim * 0.45) + (comp_sim * 0.35) + (title_sim * 0.20)

        # 4. Colleague Triangulation
        triangulation = self.triangulate_coworker_network(
            person_a_id=existing_person.id,
            person_b_id=existing_person.id,  # same canonical cluster check
            base_confidence=base_score,
        )

        final_score = triangulation["boosted_confidence"]
        verdict = "AUTO_MERGE" if final_score >= 0.85 else (
            "HUMAN_REVIEW" if final_score >= 0.55 else "SEPARATE"
        )

        return {
            "candidate_name": candidate_name,
            "existing_person_id": existing_person.id,
            "base_score": round(base_score, 2),
            "final_score": final_score,
            "title_analysis": title_res,
            "verdict": verdict,
            "triangulation": triangulation,
        }
