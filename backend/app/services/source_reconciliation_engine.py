"""
source_reconciliation_engine.py — Multi-Source Observation Fusion & Field-Level Provenance.

Fuses conflicting evidence across sources (LinkedIn, Apollo, ZoomInfo, Scout Edge, Teams, Google Chat).
Computes field-level confidence via:
  effective_confidence = base_reliability * field_weight * exp(-lambda * delta_t) * (1 + beta * min(confirmations, 3))

Preserves four distinct data tiers:
- CURRENT: Reconciled canonical facts
- HISTORY: Temporal contact & employment history (valid_from / valid_to)
- OBSERVATIONS: Raw field provenance ledger
- CONFLICTS: Quarantined disputes requiring review
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .source_connector_base import SourceConnectorRegistry

logger = logging.getLogger("talentops.reconciliation_engine")

# Decay Half-Lives in days
HALF_LIFE_DAYS = {
    "current_company": 180.0,
    "current_title": 180.0,
    "primary_email": 365.0,
    "primary_phone": 365.0,
    "full_name": 1825.0,  # 5 years
    "linkedin_url": 1095.0,
}

CONFIRMATION_BOOST_BETA = 0.10  # 10% boost per independent confirming source


class SourceReconciliationEngine:
    """
    Fuses observations across disparate sources, resolves temporal transitions,
    and quarantines intractable disputes without destructive overwrites.
    """

    @classmethod
    def calculate_effective_confidence(
        cls,
        field_name: str,
        base_reliability: float,
        field_weight: float,
        observed_at: datetime,
        confirming_sources_count: int = 1,
        now: Optional[datetime] = None,
    ) -> float:
        """
        Calculates time-decayed, multi-source boosted confidence.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Make sure observed_at has timezone
        obs_time = observed_at
        if obs_time.tzinfo is None:
            obs_time = obs_time.replace(tzinfo=timezone.utc)

        age_days = max(0.0, (now - obs_time).total_seconds() / 86400.0)
        half_life = HALF_LIFE_DAYS.get(field_name, 365.0)
        decay_constant = math.log(2) / half_life

        time_decay = math.exp(-decay_constant * age_days)
        repetition_factor = 1.0 + (CONFIRMATION_BOOST_BETA * min(max(0, confirming_sources_count - 1), 3))

        raw_score = base_reliability * field_weight * time_decay * repetition_factor
        return round(max(0.0, min(1.0, raw_score)), 4)

    @classmethod
    def reconcile_field(
        cls,
        field_name: str,
        observations: List[Dict[str, Any]],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Reconciles observations for a single field from multiple sources.
        Returns winning value, confidence, provenance, and any detected conflict.
        """
        if not observations:
            return {
                "field_name": field_name,
                "value": None,
                "confidence": 0.0,
                "status": "EMPTY",
                "conflict": None,
            }

        if now is None:
            now = datetime.now(timezone.utc)

        # Group observations by normalized value
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for obs in observations:
            val = str(obs.get("field_value", "")).strip()
            if not val:
                continue
            norm_val = val.lower() if field_name in ("primary_email", "linkedin_url") else val
            grouped.setdefault(norm_val, []).append(obs)

        if not grouped:
            return {
                "field_name": field_name,
                "value": None,
                "confidence": 0.0,
                "status": "EMPTY",
                "conflict": None,
            }

        # Score each candidate value
        scored_candidates = []
        for norm_val, obs_list in grouped.items():
            distinct_sources = set(o.get("source", "UNKNOWN") for o in obs_list)
            # Find the newest observation for this value
            newest_obs = max(obs_list, key=lambda o: o.get("observed_at") or datetime.min.replace(tzinfo=timezone.utc))
            observed_at = newest_obs.get("observed_at") or now

            # Determine source connector reliability (take highest among confirming sources)
            max_rel = 0.0
            max_field_weight = 0.0
            for src in distinct_sources:
                conn = SourceConnectorRegistry.get(src)
                if conn:
                    if conn.source_reliability > max_rel:
                        max_rel = conn.source_reliability
                    f_wt = conn.field_reliability.get(field_name, conn.source_reliability)
                    if f_wt > max_field_weight:
                        max_field_weight = f_wt
            base_rel = max_rel or 0.75
            field_weight = max_field_weight or base_rel

            eff_conf = cls.calculate_effective_confidence(
                field_name=field_name,
                base_reliability=base_rel,
                field_weight=field_weight,
                observed_at=observed_at,
                confirming_sources_count=len(distinct_sources),
                now=now,
            )

            # Preserve the original formatted value (from newest observation)
            original_val = newest_obs.get("field_value")

            scored_candidates.append({
                "value": original_val,
                "norm_value": norm_val,
                "confidence": eff_conf,
                "sources": list(distinct_sources),
                "newest_observed_at": observed_at,
                "observation_count": len(obs_list),
            })

        # Sort descending by confidence
        scored_candidates.sort(key=lambda c: c["confidence"], reverse=True)
        winner = scored_candidates[0]

        # Conflict & Career Progression Detection
        conflict = None
        status = "RESOLVED"
        if len(scored_candidates) > 1:
            runner_up = scored_candidates[1]
            conf_diff = winner["confidence"] - runner_up["confidence"]
            time_delta_days = (winner["newest_observed_at"] - runner_up["newest_observed_at"]).total_seconds() / 86400.0

            if abs(time_delta_days) > 60 and field_name in ("current_company", "current_title"):
                # Chronological progression: newer observation is current, older is history
                status = "CAREER_PROGRESSION"
            elif conf_diff < 0.15 and runner_up["confidence"] >= 0.50:
                # Concurrent dispute: both recent and close in confidence
                status = "CONFLICT_DETECTED"
                conflict = {
                    "field_name": field_name,
                    "candidate_a": winner,
                    "candidate_b": runner_up,
                    "confidence_gap": round(conf_diff, 4),
                    "reason": f"Dispute between {winner['sources']} ({winner['value']}) and {runner_up['sources']} ({runner_up['value']})",
                }
            else:
                status = "RESOLVED"

        return {
            "field_name": field_name,
            "value": winner["value"],
            "confidence": winner["confidence"],
            "sources": winner["sources"],
            "observed_at": winner["newest_observed_at"],
            "status": status,
            "conflict": conflict,
            "all_candidates": scored_candidates,
        }

    @classmethod
    def fuse_entity_observations(
        cls,
        observations: List[Dict[str, Any]],
        existing_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Fuses all observations for an entity across all fields.
        Returns CURRENT facts, temporal HISTORY events, and unresolved CONFLICTS.
        """
        # Separate observations by field
        by_field: Dict[str, List[Dict[str, Any]]] = {}
        for obs in observations:
            fn = obs.get("field_name")
            if fn:
                by_field.setdefault(fn, []).append(obs)

        current_facts: Dict[str, Any] = {}
        confidences: Dict[str, float] = {}
        provenance_sources: Dict[str, List[str]] = {}
        conflicts: List[Dict[str, Any]] = []
        history_events: List[Dict[str, Any]] = list(existing_history or [])

        target_fields = [
            "full_name",
            "current_company",
            "current_title",
            "primary_email",
            "primary_phone",
            "linkedin_url",
            "location",
        ]

        for field in target_fields:
            field_obs = by_field.get(field, [])
            res = cls.reconcile_field(field, field_obs)

            current_facts[field] = res["value"]
            confidences[field] = res["confidence"]
            provenance_sources[field] = res.get("sources", [])

            if res.get("conflict"):
                conflicts.append(res["conflict"])

            # If there's career progression or older superseded values, record in history
            candidates = res.get("all_candidates", [])
            if len(candidates) > 1 and res["value"]:
                for cand in candidates[1:]:
                    if res.get("status") == "CAREER_PROGRESSION" or cand["confidence"] >= 0.20:
                        history_events.append({
                            "field_name": field,
                            "historical_value": cand["value"],
                            "status": "historical",
                            "sources": cand["sources"],
                            "superseded_by": res["value"],
                            "observed_at": cand["newest_observed_at"].isoformat() if hasattr(cand["newest_observed_at"], "isoformat") else str(cand["newest_observed_at"]),
                        })

        # Calculate overall record quality & confidence
        valid_confs = [c for c in confidences.values() if c > 0]
        avg_confidence = round(sum(valid_confs) / len(valid_confs), 4) if valid_confs else 0.0

        return {
            "current": current_facts,
            "confidences": confidences,
            "overall_confidence": avg_confidence,
            "provenance": provenance_sources,
            "history": history_events,
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0,
        }
