"""
ai_data_query_engine.py — Natural Language Query Parser & Evidence Search Engine.

Translates human recruiting queries into structured database queries across
canonical entities, field observations, temporal history, and multi-source provenance:
- "Find people in US with verified corporate emails whose company changed recently"
- "Candidates with phone numbers verified by at least 2 sources"
- "Show me all people mentioned in Teams chats last week who don't have a LinkedIn profile"
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, or_, and_

from ..models.data_quality_models import (
    PersonIdentity,
    FieldObservation,
    PersonContactHistory,
)

logger = logging.getLogger("talentops.ai_query")


class AIDataQueryEngine:
    """
    Translates natural language questions into structured queries over multi-source evidence.
    """

    @classmethod
    def parse_query(cls, query_text: str) -> Dict[str, Any]:
        """
        Extracts structured intent, filters, and constraints from free-form natural language.
        """
        q = query_text.lower()
        filters: Dict[str, Any] = {
            "raw_query": query_text,
            "country": None,
            "company": None,
            "title_keyword": None,
            "has_corporate_email": False,
            "email_deliverable": False,
            "has_mobile_phone": False,
            "has_phone": False,
            "missing_linkedin": False,
            "min_sources": 1,
            "company_changed_recently": False,
            "sources": [],
        }

        # 1. Geographic filters
        if "in us" in q or "in the us" in q or "in united states" in q or "usa" in q:
            filters["country"] = "US"
        elif "in uk" in q or "in united kingdom" in q:
            filters["country"] = "GB"
        elif "in india" in q:
            filters["country"] = "IN"
        elif "in canada" in q:
            filters["country"] = "CA"

        # 2. Email constraints
        if "verified" in q or "deliverable" in q or "valid email" in q:
            filters["email_deliverable"] = True
        if "corporate email" in q or "business email" in q or "work email" in q:
            filters["has_corporate_email"] = True

        # 3. Phone constraints
        if "mobile" in q or "cell" in q:
            filters["has_mobile_phone"] = True
        elif "phone" in q:
            filters["has_phone"] = True

        # 4. Multi-source confirmation
        source_count_match = re.search(r"(\d+)\s+(?:or more\s+)?sources", q)
        if source_count_match:
            filters["min_sources"] = int(source_count_match.group(1))

        # 5. Career change / timeline
        if "changed" in q or "switched" in q or "left" in q or "new company" in q:
            filters["company_changed_recently"] = True

        # 6. Specific platforms
        if "teams" in q:
            filters["sources"].append("MICROSOFT_TEAMS")
        if "google chat" in q or "gchat" in q:
            filters["sources"].append("GOOGLE_CHAT")
        if "linkedin" in q and ("without" in q or "don't have" in q or "lack" in q or "missing" in q):
            filters["missing_linkedin"] = True

        # 7. Company search
        comp_match = re.search(r"(?:at|from)\s+([a-z0-9&.\-]+(?:\s+[a-z0-9&.\-]+)?)", q)
        if comp_match:
            cand = comp_match.group(1).strip()
            if cand not in ("us", "the us", "least", "any", "verified", "work"):
                filters["company"] = cand

        # 8. Title search
        title_keywords = [
            "software engineer", "devops", "architect", "product manager",
            "recruiter", "sourcer", "director", "vp", "data scientist",
            "backend", "frontend", "full stack",
        ]
        for tk in title_keywords:
            if tk in q:
                filters["title_keyword"] = tk
                break

        return filters

    @classmethod
    def execute_query(
        cls,
        db: Session,
        query_text: str,
        limit: int = 50,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Parses query and executes SQL filters against the database.
        """
        filters = cls.parse_query(query_text)
        query = db.query(PersonIdentity)

        # Apply basic filters
        if filters["country"]:
            # Check location string
            query = query.filter(PersonIdentity.location.ilike(f"%{filters['country']}%"))

        if filters["company"]:
            query = query.filter(PersonIdentity.current_company.ilike(f"%{filters['company']}%"))

        if filters["title_keyword"]:
            query = query.filter(PersonIdentity.current_title.ilike(f"%{filters['title_keyword']}%"))

        if filters["email_deliverable"]:
            query = query.filter(PersonIdentity.email_status.in_(["DELIVERABLE", "VERIFIED"]))

        if filters["has_corporate_email"]:
            query = query.filter(
                PersonIdentity.primary_email.isnot(None),
                PersonIdentity.email_role_type == "individual",
                ~PersonIdentity.primary_email.ilike("%@gmail.com%"),
                ~PersonIdentity.primary_email.ilike("%@yahoo.com%"),
                ~PersonIdentity.primary_email.ilike("%@hotmail.com%"),
                ~PersonIdentity.primary_email.ilike("%@outlook.com%"),
            )

        if filters["has_mobile_phone"] or filters["has_phone"]:
            query = query.filter(PersonIdentity.primary_phone.isnot(None))

        if filters["missing_linkedin"]:
            query = query.filter(
                or_(
                    PersonIdentity.canonical_profile_url.is_(None),
                    ~PersonIdentity.canonical_profile_url.ilike("%linkedin.com%"),
                )
            )

        # Temporal filter: company changed recently
        if filters["company_changed_recently"]:
            recent_threshold = datetime.now(timezone.utc) - timedelta(days=180)
            person_ids_with_history = (
                db.query(PersonContactHistory.person_identity_id)
                .filter(
                    PersonContactHistory.contact_type == "company",
                    PersonContactHistory.created_at >= recent_threshold,
                )
                .subquery()
            )
            query = query.filter(PersonIdentity.id.in_(person_ids_with_history))

        # Multi-source confirmation filter
        if filters["min_sources"] > 1:
            multi_source_ids = (
                db.query(FieldObservation.entity_id)
                .filter(FieldObservation.entity_type == "PERSON")
                .group_by(FieldObservation.entity_id)
                .having(sqlfunc.count(sqlfunc.distinct(FieldObservation.source)) >= filters["min_sources"])
                .subquery()
            )
            query = query.filter(PersonIdentity.id.in_(multi_source_ids))

        total_count = query.count()
        records = query.order_by(PersonIdentity.overall_quality_score.desc()).offset(skip).limit(limit).all()

        results = []
        for p in records:
            results.append({
                "id": p.id,
                "canonical_name": p.canonical_name,
                "current_title": p.current_title,
                "current_company": p.current_company,
                "primary_email": p.primary_email,
                "email_status": p.email_status,
                "primary_phone": p.primary_phone,
                "profile_url": p.canonical_profile_url,
                "location": p.location,
                "overall_quality_score": p.overall_quality_score,
                "identity_confidence": p.identity_confidence,
            })

        return {
            "query": query_text,
            "parsed_filters": filters,
            "total_matches": total_count,
            "results": results,
            "limit": limit,
            "skip": skip,
        }
