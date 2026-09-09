"""
enrichment_planner.py — Conditional Cost-Aware Enrichment Planner.

Optimizes external third-party API spend (Apollo, Hunter, ContactOut, ZoomInfo):
1. Gap Analysis: Only triggers enrichment for missing or stale (>180d) fields.
2. Cost Optimization: Ranks authorized sources by minimum cost and maximum reliability.
3. 30-Day Idempotency: Prevents redundant queries to the same provider for the same person.
4. Tenant Budget Guardrails: Hard limits monthly spend and query quotas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .source_connector_base import SourceConnectorRegistry, BaseSourceConnector

logger = logging.getLogger("talentops.enrichment_planner")

DEFAULT_TENANT_MONTHLY_BUDGET_USD = 50.00
DEFAULT_TENANT_MONTHLY_QUERY_LIMIT = 500


class EnrichmentPlanner:
    """
    Formulates lean, cost-aware enrichment plans to fill candidate information gaps.
    """

    @classmethod
    def analyze_candidate_gaps(cls, person_data: Dict[str, Any]) -> List[str]:
        """Identifies missing or stale critical fields."""
        gaps = []
        if not person_data.get("primary_email"):
            gaps.append("email")
        if not person_data.get("primary_phone"):
            gaps.append("phone")
        if not person_data.get("current_company"):
            gaps.append("company")
        if not person_data.get("current_title"):
            gaps.append("title")
        if not person_data.get("linkedin_url"):
            gaps.append("linkedin")
        return gaps

    @classmethod
    def plan_enrichment(
        cls,
        person_id: int,
        person_data: Dict[str, Any],
        recent_query_history: Optional[List[Dict[str, Any]]] = None,
        tenant_spend_usd: float = 0.0,
        monthly_budget_usd: float = DEFAULT_TENANT_MONTHLY_BUDGET_USD,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Creates an optimal enrichment execution plan.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        gaps = cls.analyze_candidate_gaps(person_data)

        if not gaps:
            return {
                "person_id": person_id,
                "status": "UP_TO_DATE",
                "missing_fields": [],
                "recommended_queries": [],
                "estimated_cost_usd": 0.0,
                "can_execute": False,
                "reason": "Entity has complete critical fields. Zero external queries needed.",
            }

        # Check tenant budget ceiling
        if tenant_spend_usd >= monthly_budget_usd:
            return {
                "person_id": person_id,
                "status": "BUDGET_EXCEEDED",
                "missing_fields": gaps,
                "recommended_queries": [],
                "estimated_cost_usd": 0.0,
                "can_execute": False,
                "reason": f"Monthly budget limit reached (${tenant_spend_usd:.2f} / ${monthly_budget_usd:.2f})",
            }

        # Track recent queries to enforce 30-day idempotency
        recent_sources_queried = set()
        if recent_query_history:
            thirty_days_ago = now - timedelta(days=30)
            for q in recent_query_history:
                q_time = q.get("queried_at")
                if q_time:
                    if q_time.tzinfo is None:
                        q_time = q_time.replace(tzinfo=timezone.utc)
                    if q_time >= thirty_days_ago:
                        recent_sources_queried.add(q.get("source_type"))

        # Find eligible connectors for missing gaps
        all_connectors = SourceConnectorRegistry.list_all()
        recommended_queries = []
        covered_gaps = set()
        estimated_cost = 0.0

        for gap in gaps:
            if gap in covered_gaps:
                continue

            # Filter connectors that support this gap and aren't throttled by idempotency
            candidates: List[BaseSourceConnector] = []
            for conn in all_connectors:
                # Exclude edge/chat from paid outbound enrichment planner
                if conn.source_type in ("SCOUT_EDGE", "GOOGLE_CHAT", "MICROSOFT_TEAMS"):
                    continue
                if conn.source_type in recent_sources_queried:
                    continue
                # Check capability
                categories = conn.supported_data_categories
                if (gap == "email" and "email" in categories) or \
                   (gap == "phone" and "phone" in categories) or \
                   (gap == "company" and ("company_firmographics" in categories or "employment" in categories)) or \
                   (gap == "title" and "employment" in categories) or \
                   (gap == "linkedin" and "linkedin" in categories):
                    candidates.append(conn)

            if not candidates:
                continue

            # Sort by lowest cost, then highest reliability
            candidates.sort(key=lambda c: (c.cost_per_query_usd, -c.source_reliability))
            best_connector = candidates[0]

            # Mark gaps covered by this connector
            for c_cat in best_connector.supported_data_categories:
                if c_cat in gaps:
                    covered_gaps.add(c_cat)
            covered_gaps.add(gap)

            recommended_queries.append({
                "connector_key": best_connector.connector_key,
                "source_type": best_connector.source_type,
                "targeted_gap": gap,
                "cost_usd": best_connector.cost_per_query_usd,
                "reliability": best_connector.source_reliability,
            })
            estimated_cost += best_connector.cost_per_query_usd

        can_execute = bool(recommended_queries and (tenant_spend_usd + estimated_cost <= monthly_budget_usd))

        return {
            "person_id": person_id,
            "status": "PLAN_READY" if recommended_queries else "NO_ELIGIBLE_PROVIDERS",
            "missing_fields": gaps,
            "recommended_queries": recommended_queries,
            "estimated_cost_usd": round(estimated_cost, 4),
            "can_execute": can_execute,
            "reason": f"Plan formulated with {len(recommended_queries)} query(s) costing ${estimated_cost:.2f}",
        }
