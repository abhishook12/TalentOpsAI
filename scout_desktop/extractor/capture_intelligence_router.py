"""Evidence-first routing for every Desktop Scout capture.

This module does not invent facts.  It decides what a capture *is useful for*
before it enters the shared pipeline, keeping profiles, companies, jobs, and
market observations from contaminating one another.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


ROUTE_PERSON = "PERSON_ENRICHMENT"
ROUTE_COMPANY = "COMPANY_INTELLIGENCE"
ROUTE_JOB = "JOB_DEMAND_INTELLIGENCE"
ROUTE_SIGNAL = "MARKET_SIGNAL_INTELLIGENCE"
ROUTE_REVIEW = "REVIEW_ONLY"
ROUTE_DROP = "DROP_NOISE"


@dataclass(frozen=True)
class CaptureRoutingDecision:
    route: str
    entity_type: str
    confidence: float
    destinations: List[str]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "destinations": self.destinations,
            "reason": self.reason,
        }


class CaptureIntelligenceRouter:
    """Maps a classified capture to its safe downstream intelligence uses."""

    _ROUTES = {
        "PERSON": (ROUTE_PERSON, ["profile_enrichment", "identity_resolution", "matching", "outreach_priority"]),
        "COMPANY": (ROUTE_COMPANY, ["company_intelligence", "account_matching", "market_map"]),
        "JOB_POSTING": (ROUTE_JOB, ["job_intelligence", "candidate_matching", "hiring_signals"]),
        "MARKET_SIGNAL": (ROUTE_SIGNAL, ["market_intelligence", "trend_signals"]),
        "CONTACT_INFO": (ROUTE_REVIEW, ["contact_review"]),
    }

    @classmethod
    def decide(cls, capture: Dict[str, Any]) -> CaptureRoutingDecision:
        entity_type = str(capture.get("entity_type") or "").upper().strip()
        page_type = str(capture.get("page_type") or "").upper().strip()
        has_name = bool(capture.get("recruiter_name") or capture.get("canonical_name"))
        has_company = bool(capture.get("company_name") or capture.get("raw_company"))
        has_job = bool(capture.get("title") or capture.get("raw_title"))
        score = capture.get("quality_score") or capture.get("confidence") or 0
        try:
            confidence = max(0.0, min(1.0, float(score) / (100.0 if float(score) > 1 else 1.0)))
        except (TypeError, ValueError):
            confidence = 0.0

        if entity_type == "NOISE" or page_type in {"FEED", "HOME", "UNKNOWN"} and not (has_name or has_company or has_job):
            return CaptureRoutingDecision(ROUTE_DROP, "NOISE", confidence, [], "No reliable entity or business signal")

        mapped = cls._ROUTES.get(entity_type)
        if mapped:
            route, destinations = mapped
            if route == ROUTE_REVIEW and not (has_name or has_company or has_job):
                return CaptureRoutingDecision(ROUTE_DROP, entity_type, confidence, [], "Contact fragment lacks an attributable entity")
            return CaptureRoutingDecision(route, entity_type, confidence, destinations, f"Classified as {entity_type}")

        # A page classifier can safely route obvious non-person pages even when
        # a platform supplied no detailed entity classification.
        if page_type in {"COMPANY_PAGE", "COMPANY"} and has_company:
            return CaptureRoutingDecision(ROUTE_COMPANY, "COMPANY", confidence, cls._ROUTES["COMPANY"][1], "Company page with attributable organization")
        if page_type in {"JOB_POSTING", "JOB"} and (has_job or has_company):
            return CaptureRoutingDecision(ROUTE_JOB, "JOB_POSTING", confidence, cls._ROUTES["JOB_POSTING"][1], "Job page with role or employer evidence")
        if has_name:
            return CaptureRoutingDecision(ROUTE_REVIEW, "PERSON", confidence, ["profile_review"], "Person evidence needs stronger classification")
        return CaptureRoutingDecision(ROUTE_REVIEW, "UNKNOWN", confidence, ["observation_review"], "Useful observation without a promotable entity")
