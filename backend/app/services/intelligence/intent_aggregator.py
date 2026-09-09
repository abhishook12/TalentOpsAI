"""
intent_aggregator.py — Event-Based Intent Engine & Explainable Evidence Aggregator.

Calculates composite intent scores (HIRING_INTENT, TECH_ADOPTION, CAREER_TRANSITION)
by aggregating discrete, weighted SignalEvents over a temporal window.
Every derived score links directly to an audit trail in the EvidenceLedger.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from ...schemas.intelligence_contracts import (
    IntentCategory,
    SignalEventType,
    EvidenceItem,
    SourceType,
)
from ...models.intelligence_models import (
    SignalEvent,
    DerivedIntent,
    EvidenceLedger,
    RawSignal,
)

logger = logging.getLogger("talentops.intelligence.intent")

# Standard event weight defaults
DEFAULT_EVENT_WEIGHTS = {
    SignalEventType.JOB_POSTED.value: 0.35,
    SignalEventType.HEADCOUNT_GROWTH.value: 0.25,
    SignalEventType.LEADERSHIP_EXPANSION.value: 0.25,
    SignalEventType.TECH_MENTIONED.value: 0.30,
    SignalEventType.POST_PUBLISHED.value: 0.15,
    SignalEventType.PROMOTION.value: 0.30,
    SignalEventType.ROLE_CHANGE.value: 0.25,
    SignalEventType.SKILL_ADDED.value: 0.20,
}


class IntentAggregator:
    def __init__(self, db: Session):
        self.db = db

    def calculate_company_hiring_intent(
        self,
        company_canonical_key: str,
        window_days: int = 90,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates HIRING_INTENT for a target company by aggregating:
        - Job postings (JOB_POSTED)
        - Headcount growth metrics (HEADCOUNT_GROWTH)
        - Leadership recruitment (LEADERSHIP_EXPANSION)
        - Expansion posts from company leaders (POST_PUBLISHED)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        events = self.db.query(SignalEvent).filter(
            SignalEvent.target_canonical_key == company_canonical_key,
            SignalEvent.event_type.in_([
                SignalEventType.JOB_POSTED.value,
                SignalEventType.HEADCOUNT_GROWTH.value,
                SignalEventType.LEADERSHIP_EXPANSION.value,
                SignalEventType.POST_PUBLISHED.value,
            ]),
        ).all()

        if not events:
            return None

        # Aggregate event weights with recency decay
        total_score_raw = 0.0
        evidence_items = []

        now_utc = datetime.now(timezone.utc)
        for ev in events:
            base_wt = ev.weight or DEFAULT_EVENT_WEIGHTS.get(ev.event_type, 0.20)
            
            # Recency factor: events within 14 days get 1.0; 90 days get 0.6
            ev_time = ev.event_timestamp
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)
            days_old = max(0, (now_utc - ev_time).days)
            decay = max(0.5, 1.0 - (days_old / window_days) * 0.5)

            contribution = base_wt * decay
            total_score_raw += contribution

            # Build evidence claim
            meta = {}
            if ev.metadata_json:
                try:
                    meta = json.loads(ev.metadata_json)
                except Exception:
                    pass

            claim = f"Observed event {ev.event_type} (weight {base_wt:.2f}, recency decay {decay:.2f})"
            if meta.get("job_title"):
                claim += f" for role '{meta.get('job_title')}'"
            elif meta.get("technology"):
                claim += f" referencing technology '{meta.get('technology')}'"

            evidence_items.append({
                "signal_event_id": ev.id,
                "claim_text": claim,
                "evidence_excerpt": f"Raw signal hash {ev.raw_signal_hash[:12]} on {ev_time.strftime('%Y-%m-%d')}",
                "observed_at": ev_time,
                "confidence": round(min(1.0, 0.70 + (contribution * 0.5)), 2),
            })

        # Calculate final composite score (0-100)
        final_score = min(98, round(total_score_raw * 100))
        if final_score < 20 and len(events) >= 1:
            final_score = min(60, len(events) * 25)

        # Confidence is higher when multiple distinct signal types agree
        unique_types = len(set(e.event_type for e in events))
        confidence = 0.95 if unique_types >= 3 else (0.85 if unique_types == 2 else 0.70)

        # Upsert DerivedIntent
        intent_record = self.db.query(DerivedIntent).filter(
            DerivedIntent.target_canonical_key == company_canonical_key,
            DerivedIntent.intent_category == IntentCategory.HIRING_INTENT.value,
        ).first()

        if not intent_record:
            intent_record = DerivedIntent(
                target_canonical_key=company_canonical_key,
                intent_category=IntentCategory.HIRING_INTENT.value,
                score=final_score,
                confidence=confidence,
                calculated_at=now_utc,
            )
            self.db.add(intent_record)
            self.db.flush()
        else:
            intent_record.score = final_score
            intent_record.confidence = confidence
            intent_record.calculated_at = now_utc

        # Write to EvidenceLedger
        # Remove old evidence rows for this intent
        self.db.query(EvidenceLedger).filter(
            EvidenceLedger.derived_intent_id == intent_record.id
        ).delete()

        for ev_item in evidence_items:
            self.db.add(EvidenceLedger(
                derived_intent_id=intent_record.id,
                signal_event_id=ev_item["signal_event_id"],
                claim_text=ev_item["claim_text"],
                evidence_excerpt=ev_item["evidence_excerpt"],
                observed_at=ev_item["observed_at"],
                confidence=ev_item["confidence"],
            ))

        self.db.commit()

        return {
            "canonical_key": company_canonical_key,
            "intent_category": IntentCategory.HIRING_INTENT.value,
            "score": final_score,
            "confidence": confidence,
            "evidence_count": len(evidence_items),
            "evidence": evidence_items,
        }

    def calculate_tech_adoption_intent(
        self,
        entity_canonical_key: str,
        technology_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates TECHNOLOGY_ADOPTION intent when multiple events reference a tech stack.
        """
        events = self.db.query(SignalEvent).filter(
            SignalEvent.target_canonical_key == entity_canonical_key,
            SignalEvent.event_type == SignalEventType.TECH_MENTIONED.value,
        ).all()

        matching_events = []
        for ev in events:
            try:
                meta = json.loads(ev.metadata_json or "{}")
                if meta.get("technology", "").lower() == technology_name.lower():
                    matching_events.append(ev)
            except Exception:
                pass

        if not matching_events:
            return None

        total_weight = sum(e.weight or 0.30 for e in matching_events)
        score = min(95, round(total_weight * 100))
        confidence = min(0.95, 0.70 + (len(matching_events) * 0.10))

        intent_category = IntentCategory.TECHNOLOGY_ADOPTION.value
        intent_record = DerivedIntent(
            target_canonical_key=entity_canonical_key,
            intent_category=f"{intent_category}:{technology_name.upper()}",
            score=score,
            confidence=confidence,
        )
        self.db.add(intent_record)
        self.db.flush()

        for ev in matching_events:
            self.db.add(EvidenceLedger(
                derived_intent_id=intent_record.id,
                signal_event_id=ev.id,
                claim_text=f"Technology '{technology_name}' mentioned in post observation",
                evidence_excerpt=f"Raw signal hash {ev.raw_signal_hash[:12]}",
                observed_at=ev.event_timestamp,
                confidence=confidence,
            ))

        self.db.commit()

        return {
            "canonical_key": entity_canonical_key,
            "technology": technology_name,
            "score": score,
            "confidence": confidence,
            "evidence_count": len(matching_events),
        }
