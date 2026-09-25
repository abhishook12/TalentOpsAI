"""
test_geographic_classifier.py — Unit Tests for Geographic Classifier & Quota Tracker.
"""

import sys
import os
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.geographic_classifier import (
    GeographicClassifier,
    GeoClassification,
    NORTH_AMERICA,
    UK,
    SOUTH_AMERICA,
    OTHER,
    UNKNOWN,
)
from backend.app.services.geo_quota_tracker import GeoQuotaTracker


@pytest.fixture
def classifier():
    return GeographicClassifier()


@pytest.fixture
def tracker():
    return GeoQuotaTracker(na_target_percent=90)


# ═══════════════════════════════════════════════════════════════════════
# Location String Parsing Tests
# ═══════════════════════════════════════════════════════════════════════

class TestLocationParsing:
    """Tests for _parse_location() signal."""

    def test_us_city_state_postal(self, classifier):
        assert classifier._parse_location("San Francisco, CA") == NORTH_AMERICA

    def test_us_city_state_full(self, classifier):
        assert classifier._parse_location("Austin, Texas") == NORTH_AMERICA

    def test_us_greater_area(self, classifier):
        assert classifier._parse_location("Greater Seattle Area") == NORTH_AMERICA

    def test_us_city_country(self, classifier):
        assert classifier._parse_location("New York, United States") == NORTH_AMERICA

    def test_canada_city(self, classifier):
        assert classifier._parse_location("Toronto, Ontario") == NORTH_AMERICA

    def test_canada_province(self, classifier):
        assert classifier._parse_location("Vancouver, British Columbia") == NORTH_AMERICA

    def test_uk_london(self, classifier):
        assert classifier._parse_location("London, England") == UK

    def test_uk_manchester(self, classifier):
        assert classifier._parse_location("Manchester, UK") == UK

    def test_uk_edinburgh(self, classifier):
        assert classifier._parse_location("Edinburgh") == UK

    def test_uk_united_kingdom(self, classifier):
        assert classifier._parse_location("Birmingham, United Kingdom") == UK

    def test_sa_sao_paulo(self, classifier):
        assert classifier._parse_location("São Paulo, Brazil") == SOUTH_AMERICA

    def test_sa_buenos_aires(self, classifier):
        assert classifier._parse_location("Buenos Aires") == SOUTH_AMERICA

    def test_sa_bogota(self, classifier):
        assert classifier._parse_location("Bogotá, Colombia") == SOUTH_AMERICA

    def test_sa_lima(self, classifier):
        assert classifier._parse_location("Lima, Peru") == SOUTH_AMERICA

    def test_other_mumbai(self, classifier):
        assert classifier._parse_location("Mumbai, India") == OTHER

    def test_other_berlin(self, classifier):
        assert classifier._parse_location("Berlin, Germany") == OTHER

    def test_other_tokyo(self, classifier):
        assert classifier._parse_location("Tokyo, Japan") == OTHER

    def test_other_sydney(self, classifier):
        assert classifier._parse_location("Sydney, Australia") == OTHER

    def test_other_bangalore(self, classifier):
        assert classifier._parse_location("Bangalore, Karnataka") == OTHER

    def test_unknown_empty(self, classifier):
        assert classifier._parse_location("") == UNKNOWN

    def test_unknown_none(self, classifier):
        assert classifier._parse_location(None) == UNKNOWN

    def test_unknown_remote(self, classifier):
        # "Remote" alone doesn't indicate a specific region
        result = classifier._parse_location("Remote")
        assert result in (UNKNOWN, NORTH_AMERICA)  # Could be either depending on impl

    def test_us_dallas_fort_worth(self, classifier):
        assert classifier._parse_location("Dallas-Fort Worth") == NORTH_AMERICA

    def test_us_salt_lake_city(self, classifier):
        assert classifier._parse_location("Salt Lake City, UT") == NORTH_AMERICA

    def test_us_raleigh(self, classifier):
        assert classifier._parse_location("Raleigh, NC") == NORTH_AMERICA

    def test_greater_london_area(self, classifier):
        assert classifier._parse_location("Greater London Area") == UK


# ═══════════════════════════════════════════════════════════════════════
# Phone Prefix Tests
# ═══════════════════════════════════════════════════════════════════════

class TestPhoneInference:
    """Tests for _infer_from_phone() signal."""

    def test_us_phone(self, classifier):
        assert classifier._infer_from_phone("+1 (555) 123-4567") == NORTH_AMERICA

    def test_uk_phone(self, classifier):
        assert classifier._infer_from_phone("+44 20 7946 0958") == UK

    def test_brazil_phone(self, classifier):
        assert classifier._infer_from_phone("+55 11 91234-5678") == SOUTH_AMERICA

    def test_argentina_phone(self, classifier):
        assert classifier._infer_from_phone("+54 11 4567-8901") == SOUTH_AMERICA

    def test_us_10digit(self, classifier):
        assert classifier._infer_from_phone("5551234567") == NORTH_AMERICA

    def test_unknown_phone(self, classifier):
        assert classifier._infer_from_phone(None) == UNKNOWN


# ═══════════════════════════════════════════════════════════════════════
# Email TLD Tests
# ═══════════════════════════════════════════════════════════════════════

class TestEmailTLD:
    """Tests for _infer_from_email_tld() signal."""

    def test_uk_email(self, classifier):
        assert classifier._infer_from_email_tld("john@example.co.uk") == UK

    def test_brazil_email(self, classifier):
        assert classifier._infer_from_email_tld("maria@empresa.br") == SOUTH_AMERICA

    def test_com_email(self, classifier):
        # .com is too ambiguous, should return UNKNOWN
        assert classifier._infer_from_email_tld("john@google.com") == UNKNOWN

    def test_no_email(self, classifier):
        assert classifier._infer_from_email_tld(None) == UNKNOWN


# ═══════════════════════════════════════════════════════════════════════
# Name-Origin Tests
# ═══════════════════════════════════════════════════════════════════════

class TestNameOrigin:
    """Tests for _infer_from_name() signal."""

    def test_hispanic_surname(self, classifier):
        region, detail = classifier._infer_from_name("Carlos Rodriguez")
        assert region == SOUTH_AMERICA

    def test_anglo_first_name(self, classifier):
        region, detail = classifier._infer_from_name("Michael Johnson")
        assert region == NORTH_AMERICA

    def test_british_first_name(self, classifier):
        region, detail = classifier._infer_from_name("Alistair Smith")
        assert region == UK

    def test_unknown_name(self, classifier):
        region, detail = classifier._infer_from_name("Rajesh Kumar")
        assert region == UNKNOWN


# ═══════════════════════════════════════════════════════════════════════
# Company HQ Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCompanyHQ:
    """Tests for _infer_from_company() signal."""

    def test_google(self, classifier):
        assert classifier._infer_from_company("Google") == NORTH_AMERICA

    def test_barclays(self, classifier):
        assert classifier._infer_from_company("Barclays") == UK

    def test_nubank(self, classifier):
        assert classifier._infer_from_company("Nubank") == SOUTH_AMERICA

    def test_unknown_company(self, classifier):
        assert classifier._infer_from_company("Random Startup LLC") == UNKNOWN


# ═══════════════════════════════════════════════════════════════════════
# Full Classification Tests (Multi-Signal)
# ═══════════════════════════════════════════════════════════════════════

class TestFullClassification:
    """Tests for the full classify() pipeline."""

    def test_strong_na_candidate(self, classifier):
        result = classifier.classify(
            raw_location="San Francisco, CA",
            raw_name="Michael Johnson",
            raw_email="michael@google.com",
            raw_company="Google",
        )
        assert result.region == NORTH_AMERICA
        assert result.confidence >= 0.45
        assert result.passes_filter is True

    def test_strong_uk_candidate(self, classifier):
        result = classifier.classify(
            raw_location="London, England",
            raw_name="Alistair Brown",
            raw_email="alistair@barclays.co.uk",
            raw_company="Barclays",
        )
        assert result.region == UK
        assert result.passes_filter is True

    def test_strong_sa_candidate(self, classifier):
        result = classifier.classify(
            raw_location="São Paulo, Brazil",
            raw_name="Carlos Rodriguez",
            raw_email="carlos@nubank.br",
            raw_company="Nubank",
        )
        assert result.region == SOUTH_AMERICA
        assert result.passes_filter is True

    def test_other_region_rejected(self, classifier):
        result = classifier.classify(
            raw_location="Mumbai, India",
            raw_name="Rajesh Kumar",
        )
        assert result.region == OTHER
        assert result.passes_filter is False

    def test_unknown_with_no_signals(self, classifier):
        result = classifier.classify()
        assert result.region == UNKNOWN

    def test_conflicting_signals_location_wins(self, classifier):
        """Location signal should dominate when present."""
        result = classifier.classify(
            raw_location="New York, NY",
            raw_name="Carlos Fernandez",  # Hispanic name → SA signal
            raw_company="Google",  # NA company
        )
        # Location (0.45 weight) + Company (0.10) → NA wins over Name (0.10 → SA)
        assert result.region == NORTH_AMERICA


# ═══════════════════════════════════════════════════════════════════════
# Quota Tracker Tests
# ═══════════════════════════════════════════════════════════════════════

class TestGeoQuotaTracker:
    """Tests for the per-cycle quota enforcer."""

    def test_accepts_first_candidate(self, tracker):
        assert tracker.should_accept(NORTH_AMERICA) is True

    def test_always_rejects_other(self, tracker):
        assert tracker.should_accept(OTHER) is False

    def test_na_quota_enforcement(self, tracker):
        # Accept 9 NA candidates
        for _ in range(9):
            tracker.record_accepted(NORTH_AMERICA)
        # 10th should still be accepted (90% of 10 = 9, but soft overflow allows it)
        assert tracker.should_accept(NORTH_AMERICA) is True

    def test_non_na_quota_enforcement(self, tracker):
        # Accept 9 NA candidates and 1 UK
        for _ in range(9):
            tracker.record_accepted(NORTH_AMERICA)
        tracker.record_accepted(UK)
        # UK is at 10%, should still have some room with soft overflow
        assert tracker.should_accept(UK) is True

    def test_stats_output(self, tracker):
        tracker.record_accepted(NORTH_AMERICA)
        tracker.record_accepted(NORTH_AMERICA)
        tracker.record_accepted(UK)
        stats = tracker.get_stats()
        assert stats["total_accepted"] == 3
        assert stats["counts"][NORTH_AMERICA] == 2
        assert stats["counts"][UK] == 1

    def test_reset(self, tracker):
        tracker.record_accepted(NORTH_AMERICA)
        tracker.reset()
        assert tracker._total_accepted == 0
        assert tracker.counts[NORTH_AMERICA] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
