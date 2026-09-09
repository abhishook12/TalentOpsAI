"""
TalentOps AI - Temporal Reconciliation & Career Timeline Engine
Reconciles conflicting observations across multiple sources and timestamps.
Constructs chronological employment trajectories, detects impossible timelines,
and safely preserves historical positions without overwriting history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("talentops.temporal_reconciler")

CURRENT_SYSTEM_YEAR = 2026


@dataclass
class CareerPosition:
    company: str
    title: str
    start_year: int
    end_year: Optional[int] = None  # None indicates current position
    source: str = "observed"
    confidence: float = 0.85
    is_current: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "title": self.title,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "duration_str": f"{self.start_year} - {self.end_year if self.end_year else 'Present'}",
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "is_current": self.is_current,
        }


@dataclass
class TimelineValidationResult:
    is_valid: bool
    positions: List[CareerPosition]
    current_position: Optional[CareerPosition]
    anomalies: List[Dict[str, Any]]
    explanation: str


class TemporalReconciler:
    """
    Constructs chronological career trajectories and detects impossible dates/conflicts.
    """

    @classmethod
    def validate_and_reconcile_positions(
        cls,
        raw_positions: List[Dict[str, Any]],
        current_year: int = CURRENT_SYSTEM_YEAR,
    ) -> TimelineValidationResult:
        """
        Validates date ranges, detects future dates or negative spans,
        and constructs an ordered chronological timeline.
        """
        anomalies: List[Dict[str, Any]] = []
        parsed_positions: List[CareerPosition] = []

        for idx, item in enumerate(raw_positions):
            company = str(item.get("company", "")).strip()
            title = str(item.get("title", "")).strip()
            start_yr = item.get("start_year")
            end_yr = item.get("end_year")
            source = item.get("source", "observed")
            conf = float(item.get("confidence", 0.85))

            if not company:
                continue

            # Check 1: Future-dated start or end date
            if start_yr and start_yr > current_year:
                anomalies.append({
                    "type": "FUTURE_DATED_EXPERIENCE",
                    "severity": "HIGH",
                    "detail": f"Position at {company} has future start year {start_yr} (current year: {current_year})",
                    "position_index": idx,
                    "field": "start_year",
                    "value": start_yr,
                })
            if end_yr and end_yr > current_year:
                anomalies.append({
                    "type": "FUTURE_DATED_EXPERIENCE",
                    "severity": "HIGH",
                    "detail": f"Position at {company} has future end year {end_yr} (current year: {current_year})",
                    "position_index": idx,
                    "field": "end_year",
                    "value": end_yr,
                })

            # Check 2: Negative duration (start > end)
            if start_yr and end_yr and start_yr > end_yr:
                anomalies.append({
                    "type": "INVALID_DATE_RANGE",
                    "severity": "CRITICAL",
                    "detail": f"Negative career duration at {company}: start {start_yr} is after end {end_yr}",
                    "position_index": idx,
                    "field": "date_range",
                    "value": f"{start_yr}-{end_yr}",
                })

            parsed_positions.append(
                CareerPosition(
                    company=company,
                    title=title,
                    start_year=start_yr or 2020,
                    end_year=end_yr,
                    source=source,
                    confidence=conf,
                    is_current=(end_yr is None or end_yr == current_year),
                )
            )

        # Sort positions chronologically by start year
        parsed_positions.sort(key=lambda p: (p.start_year, p.end_year or 9999))

        # Check 3: Same-period contradictory employers
        for i in range(len(parsed_positions) - 1):
            p1 = parsed_positions[i]
            p2 = parsed_positions[i + 1]
            # If both active during the same time with totally different companies
            if p1.start_year == p2.start_year and p1.company.lower() != p2.company.lower():
                if p1.is_current and p2.is_current:
                    anomalies.append({
                        "type": "TIMELINE_CONFLICT",
                        "severity": "HIGH",
                        "detail": f"Simultaneous conflicting full-time roles: {p1.title} @ {p1.company} vs {p2.title} @ {p2.company}",
                        "field": "company",
                        "value": f"{p1.company} / {p2.company}",
                    })

        # Determine current canonical position
        current_pos = None
        for p in reversed(parsed_positions):
            if p.is_current:
                current_pos = p
                break
        if not current_pos and parsed_positions:
            current_pos = parsed_positions[-1]
            current_pos.is_current = True

        is_valid = len([a for a in anomalies if a["severity"] in ("CRITICAL", "HIGH")]) == 0
        explanation = (
            f"Successfully reconciled {len(parsed_positions)} career positions into chronological trajectory. "
            f"Current active role: {current_pos.title if current_pos else 'None'} @ {current_pos.company if current_pos else 'None'}."
        ) if is_valid else f"Detected {len(anomalies)} timeline anomaly issues requiring review or quarantine."

        return TimelineValidationResult(
            is_valid=is_valid,
            positions=parsed_positions,
            current_position=current_pos,
            anomalies=anomalies,
            explanation=explanation,
        )

    @classmethod
    def reconcile_observations(
        cls,
        observations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Takes raw observations across multiple sources and timestamps,
        e.g.:
          Source A (2024): VP Engineering @ ABC
          Source B (2025): VP Engineering @ XYZ
          Source C (2026): CTO @ XYZ
        Returns temporal conclusion and recommended current values.
        """
        if not observations:
            return {"current_title": None, "current_company": None, "trajectory": []}

        # Normalize timestamps
        sorted_obs = sorted(
            observations,
            key=lambda x: str(x.get("observed_at", "")),
        )

        trajectory = []
        for o in sorted_obs:
            trajectory.append({
                "source": o.get("source", "unknown"),
                "company": o.get("company"),
                "title": o.get("title"),
                "observed_at": str(o.get("observed_at")),
            })

        latest = sorted_obs[-1]
        return {
            "current_title": latest.get("title"),
            "current_company": latest.get("company"),
            "trajectory": trajectory,
            "latest_source": latest.get("source"),
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
        }
