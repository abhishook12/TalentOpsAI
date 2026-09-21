"""
backend/app/services/autonomous_teacher_service.py — Autonomous AI Teacher & Entity Adjudicator

Implements the "Human-out-of-the-Loop" active learning engine:
1. Receives ambiguous entity observations buffered from Scout Desktop instances.
2. Uses Google Gemini (via AIRouterService) to adjudicate the ground truth from raw spatial context.
3. Automatically promotes verified entities into the canonical Knowledge Graph (KnowledgeEntity).
4. Serves incremental knowledge deltas to all Fleet Scout instances for zero-restart continuous learning.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.knowledge_models import KnowledgeEntity, SemanticObservation
from ..services.ai_router_service import AIRouterService

logger = logging.getLogger("talentops.autonomous_teacher")

VALID_ENTITY_TYPES = {
    "COMPANY", "PERSON", "JOB_TITLE", "SKILL", "SECTION_HEADER",
    "WORKPLACE_TYPE", "EDUCATION", "LOCATION", "UI_NOISE"
}


class AutonomousTeacherService:
    """
    Autonomous Entity Adjudicator and Training Engine.
    Executes asynchronous background teacher passes without human intervention.
    """

    @staticmethod
    def adjudicate_observation(
        candidate_text: str,
        context_lines: List[str],
        source_url: str = "",
        window_title: str = "",
        owner_user_id: int = 1,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes a teacher adjudication pass on a single ambiguous observation.
        Analyzes surrounding context to deduce ground truth classification.
        """
        ctx_formatted = "\n".join(f"  - {line}" for line in context_lines) if context_lines else "  (No context provided)"
        
        prompt = f"""You are the TalentOps Chief Semantic Entity Adjudicator.
Your task is to analyze an ambiguous text snippet extracted by Desktop Scout from a recruiter's workstation and determine its true semantic category.

TARGET TEXT TO CLASSIFY: "{candidate_text}"

SURROUNDING SCREEN CONTEXT LINES:
{ctx_formatted}

METADATA:
- Source URL: "{source_url}"
- Active Window Title: "{window_title}"

CLASSIFICATION RULES:
1. 'COMPANY': A business entity, employer, corporation, staffing firm, or commercial organization (e.g. 'Tek Inspirations', 'Kochar Tech', 'Google', 'Amazon Web Services').
2. 'PERSON': An individual human candidate or employee name (e.g. 'Abhishek Jadon', 'Mohit Tiwari', 'Satya Nadella').
3. 'JOB_TITLE': A professional role or title (e.g. 'Senior Software Engineer', 'Talent Sourcer').
4. 'SKILL': A technical proficiency, language, framework, or tool (e.g. 'Python', 'Kubernetes').
5. 'SECTION_HEADER': A resume or profile section title (e.g. 'Experience', 'About', 'Education', 'Overview').
6. 'WORKPLACE_TYPE': Employment arrangement (e.g. 'Full-time', 'Contract', 'Hybrid', 'Remote').
7. 'EDUCATION': An academic degree or educational institution (e.g. 'Stanford University', 'B.S. Computer Science').
8. 'LOCATION': A city, state, country, or metro area (e.g. 'San Francisco, CA', 'Bengaluru, India').
9. 'UI_NOISE': A button, badge, count, action, or social metric (e.g. 'Open to work', 'Connect', '500+ connections').

OUTPUT FORMAT:
Return valid JSON only (no markdown, no preamble):
{{
  "entity_type": "COMPANY|PERSON|JOB_TITLE|SKILL|SECTION_HEADER|WORKPLACE_TYPE|EDUCATION|LOCATION|UI_NOISE",
  "canonical_name": "Properly capitalized clean name",
  "confidence": 0.0 to 1.0,
  "reasoning": "Concise factual reason based on the context",
  "is_promotable": true or false
}}
"""

        result_dict, model_used, latency_ms = AIRouterService.execute_prompt(
            prompt=prompt,
            action_type="autonomous_entity_adjudication",
            user_id=owner_user_id,
            db=db,
            preferred_model="gemini-2.5-flash",
        )

        entity_type = (result_dict.get("entity_type") or "UNKNOWN").upper().strip()
        canonical_name = (result_dict.get("canonical_name") or candidate_text).strip()
        confidence = float(result_dict.get("confidence") or 0.85)
        reasoning = result_dict.get("reasoning") or "Heuristic evaluation"

        if entity_type not in VALID_ENTITY_TYPES:
            entity_type = "UNKNOWN"

        logger.info(
            "AI Teacher adjudicated '%s' -> %s (conf=%.2f, model=%s, latency=%dms): %s",
            candidate_text, entity_type, confidence, model_used, latency_ms, reasoning
        )

        # Auto-promote to KnowledgeEntity if high confidence
        promoted_id = None
        if db and confidence >= 0.88 and entity_type in {"COMPANY", "UI_NOISE", "SKILL", "JOB_TITLE", "SECTION_HEADER"}:
            try:
                # Check if already exists in KnowledgeEntity
                existing = db.query(KnowledgeEntity).filter(
                    func.lower(KnowledgeEntity.canonical_name) == canonical_name.lower(),
                    KnowledgeEntity.entity_type == entity_type
                ).first()

                if not existing:
                    new_ent = KnowledgeEntity(
                        owner_user_id=owner_user_id,
                        entity_type=entity_type,
                        canonical_name=canonical_name,
                        confidence=confidence,
                        source_url=source_url,
                        attributes_json=json.dumps({
                            "learning_mode": "AUTONOMOUS_TEACHER",
                            "model_used": model_used,
                            "reasoning": reasoning,
                            "original_text": candidate_text,
                            "adjudicated_at": time.time(),
                        }),
                    )
                    db.add(new_ent)
                    db.commit()
                    db.refresh(new_ent)
                    promoted_id = new_ent.id
                    logger.info("🎉 Auto-promoted '%s' (%s) to KnowledgeEntity id=%d", canonical_name, entity_type, promoted_id)
                else:
                    promoted_id = existing.id
            except Exception as e:
                logger.warning("Could not commit promoted KnowledgeEntity: %s", e)
                try:
                    db.rollback()
                except Exception:
                    pass

        return {
            "entity_type": entity_type,
            "canonical_name": canonical_name,
            "confidence": confidence,
            "reasoning": reasoning,
            "model_used": model_used,
            "promoted_id": promoted_id,
            "adjudicated_at": time.time(),
        }

    @staticmethod
    def process_batch(
        observations: List[Dict[str, Any]],
        owner_user_id: int = 1,
        db: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """Processes a batch of ambiguous observations and returns adjudication results."""
        results = []
        for obs in observations:
            text = obs.get("candidate_text")
            if not text:
                continue
            ctx = obs.get("context_lines", [])
            url = obs.get("source_url", "")
            wt = obs.get("window_title", "")
            adj = AutonomousTeacherService.adjudicate_observation(
                candidate_text=text,
                context_lines=ctx,
                source_url=url,
                window_title=wt,
                owner_user_id=owner_user_id,
                db=db,
            )
            results.append(adj)
        return results

    @staticmethod
    def get_fleet_knowledge_deltas(
        since_timestamp: float = 0.0,
        db: Optional[Session] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves newly learned or verified entities discovered since since_timestamp
        for zero-restart synchronization down to Fleet Scout Desktop instances.
        """
        if not db:
            return []

        try:
            query = db.query(KnowledgeEntity)
            if since_timestamp > 0:
                since_dt = datetime.fromtimestamp(since_timestamp, tz=timezone.utc)
                query = query.filter(KnowledgeEntity.created_at >= since_dt)

            entities = query.order_by(KnowledgeEntity.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": ent.id,
                    "entity_type": ent.entity_type,
                    "canonical_name": ent.canonical_name,
                    "confidence": ent.confidence or 0.95,
                    "created_at": ent.created_at.timestamp() if ent.created_at else time.time(),
                }
                for ent in entities
            ]
        except Exception as e:
            logger.warning("Error querying fleet knowledge deltas: %s", e)
            return []
