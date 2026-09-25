"""
geo_quota_tracker.py — Per-Cycle Geographic Quota Enforcement.

Tracks the running count of accepted candidates by region within a single
harvest cycle and enforces the 90% NA / 10% UK+SA distribution rule.

Usage:
    tracker = GeoQuotaTracker()
    tracker.record_accepted("NORTH_AMERICA")
    tracker.should_accept("UK")  → True/False based on current ratio
"""

import logging
from typing import Dict

from ..config import GEO_NA_TARGET_PERCENT, GEO_FILTER_ENABLED, GEO_ALLOWED_REGIONS

logger = logging.getLogger("talentops.geo_quota")

NORTH_AMERICA = "NORTH_AMERICA"
UK = "UK"
SOUTH_AMERICA = "SOUTH_AMERICA"
OTHER = "OTHER"
UNKNOWN = "UNKNOWN"


class GeoQuotaTracker:
    """
    Stateful per-cycle quota enforcer.
    Tracks running counts and enforces the NA/non-NA distribution ratio.
    Resets at the start of each harvest cycle.
    """

    def __init__(self, na_target_percent: int = None):
        self.na_target = na_target_percent or GEO_NA_TARGET_PERCENT
        self.counts: Dict[str, int] = {
            NORTH_AMERICA: 0,
            UK: 0,
            SOUTH_AMERICA: 0,
            OTHER: 0,
            UNKNOWN: 0,
        }
        self._total_accepted = 0

    def record_accepted(self, region: str) -> None:
        """Record a candidate acceptance for quota tracking."""
        if region in self.counts:
            self.counts[region] += 1
        else:
            self.counts[region] = 1
        self._total_accepted += 1

    def should_accept(self, region: str) -> bool:
        """
        Determines whether a candidate with the given region should be accepted
        based on the current quota distribution.
        
        Rules:
          - OTHER region → always reject
          - UNKNOWN region → accept (handled by classifier's GEO_REJECT_UNKNOWN)
          - NA: accept if current NA% <= target (allow soft overflow)
          - UK/SA: accept if current non-NA% < (100 - target)%
        """
        if not GEO_FILTER_ENABLED:
            return True

        # Hard block on OTHER — no exceptions
        if region == OTHER:
            return False

        # Hard block on regions not in the allowlist
        if region not in GEO_ALLOWED_REGIONS and region != UNKNOWN:
            return False

        # UNKNOWN passes through (classifier handles this separately)
        if region == UNKNOWN:
            return True

        # If we haven't accepted anyone yet, accept the first candidate
        if self._total_accepted == 0:
            return True

        na_count = self.counts.get(NORTH_AMERICA, 0)
        non_na_count = self.counts.get(UK, 0) + self.counts.get(SOUTH_AMERICA, 0)

        if region == NORTH_AMERICA:
            # North America is the primary target (>=90%) — always accept NA.
            return True
        else:
            # UK or SA: accept only if non-NA quota has room (<= 10% + 2% tolerance)
            max_non_na_pct = 100 - self.na_target  # e.g. 10%
            current_non_na_pct = (non_na_count / self._total_accepted) * 100 if self._total_accepted > 0 else 0
            return current_non_na_pct <= (max_non_na_pct + 2)

    def get_stats(self) -> Dict[str, any]:
        """Returns current quota statistics."""
        total = self._total_accepted or 1  # avoid division by zero
        return {
            "total_accepted": self._total_accepted,
            "counts": dict(self.counts),
            "percentages": {
                region: round((count / total) * 100, 1)
                for region, count in self.counts.items()
                if count > 0
            },
            "na_target_percent": self.na_target,
            "na_current_percent": round((self.counts.get(NORTH_AMERICA, 0) / total) * 100, 1),
        }

    def reset(self) -> None:
        """Resets all counters for a new harvest cycle."""
        for key in self.counts:
            self.counts[key] = 0
        self._total_accepted = 0

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"GeoQuotaTracker(total={stats['total_accepted']}, NA={stats['na_current_percent']}%)"
