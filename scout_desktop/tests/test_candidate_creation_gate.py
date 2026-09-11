"""
tests/test_candidate_creation_gate.py — Regression Test Suite for Candidate Creation Gate

Verifies the hard architectural boundaries:
1. Rejection of all 9 UI noise strings and fragments from user prompt.
2. Normalization of "Active Window" platform.
3. Neutralization of corrupted OCR locations (e.g. "San \ufffdntu\ufffd").
4. Acceptance and full verification of legitimate profiles (e.g. Sarah Chen).
5. Strict 3-Tier enforcement: RAW OBSERVATION != CANDIDATE.
"""

import pytest
from scout_desktop.extractor.candidate_gate import (
    create_candidate_if_valid,
    normalize_platform,
    sanitize_location,
    CandidateGateResult,
)
from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
)


class TestCandidateCreationGate:
    """Rigorous regression tests for Candidate Creation Gate."""

    # ─────────────────────────────────────────────────────────────
    # 1. Verification of the 9 Bad UI / Navigation Noise Strings
    # ─────────────────────────────────────────────────────────────
    @pytest.mark.parametrize(
        "bad_name",
        [
            "Myridius: People",
            "CTO: Overview",
            "CTO: People",
            "REASON: Overview",
            "REASON: People",
            "355 M Inbox (121)",
            "54 Ri Ht...",
            "iHHI",
            "My",
        ],
    )
    def test_bad_ui_noise_strings_rejected_at_gate(self, bad_name):
        """Every single UI/navigation noise string must be rejected before becoming a candidate."""
        obs = {
            "name": bad_name,
            "title": "Software Engineer",
            "company": "Tech Corp",
            "platform": "Active Window",
        }
        res = create_candidate_if_valid(obs)
        assert res.is_valid_candidate is False
        assert res.status in ("REJECTED", "REVIEW_REQUIRED")
        assert res.decision in ("UNRESOLVED_UI_TEXT", "REJECTED_OBSERVATION")

    def test_individual_noise_pattern_rejection(self):
        """Pattern-level validation rejects colon, ellipses, acronym prefixes, and fragments."""
        assert not is_valid_person_name("Myridius: People")
        assert not is_valid_person_name("CTO: Overview")
        assert not is_valid_person_name("CTO: People")
        assert not is_valid_person_name("REASON: Overview")
        assert not is_valid_person_name("REASON: People")
        assert not is_valid_person_name("355 M Inbox (121)")
        assert not is_valid_person_name("54 Ri Ht...")
        assert not is_valid_person_name("iHHI")
        assert not is_valid_person_name("My")

    # ─────────────────────────────────────────────────────────────
    # 2. Platform Normalization ("Active Window" -> DESKTOP_CAPTURE)
    # ─────────────────────────────────────────────────────────────
    def test_active_window_platform_normalized(self):
        """'Active Window' must NEVER be preserved as a platform string."""
        assert normalize_platform("Active Window") == "DESKTOP_CAPTURE"
        assert normalize_platform("active window") == "DESKTOP_CAPTURE"
        assert (
            normalize_platform("Active Window", source_url="https://www.linkedin.com/in/sarah-chen")
            == "LinkedIn"
        )
        assert (
            normalize_platform("Active Window", source_url="https://app.zoominfo.com/#/search")
            == "ZoomInfo"
        )

    # ─────────────────────────────────────────────────────────────
    # 3. Corrupted OCR Location Neutralization
    # ─────────────────────────────────────────────────────────────
    def test_corrupted_location_neutralization(self):
        """Corrupted OCR locations like 'San \ufffdntu\ufffd' must be set to None / NEEDS_REVIEW."""
        cleaned, is_corrupted = sanitize_location("San \ufffdntu\ufffd")
        assert is_corrupted is True
        assert cleaned is None

        cleaned_valid, is_corrupted_valid = sanitize_location("San Francisco, CA")
        assert is_corrupted_valid is False
        assert cleaned_valid == "San Francisco, CA"

    # ─────────────────────────────────────────────────────────────
    # 4. Legitimate Candidate Verification (Sarah Chen)
    # ─────────────────────────────────────────────────────────────
    def test_legitimate_candidate_verified(self):
        """Legitimate profile (Sarah Chen) passes with >= 70 quality score and >= 0.75 confidence."""
        obs = {
            "name": "Sarah Chen",
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco, CA",
            "linkedin_url": "https://www.linkedin.com/in/sarah-chen?trk=public_profile",
            "platform": "Active Window",
            "source_url": "https://www.linkedin.com/in/sarah-chen",
        }
        res = create_candidate_if_valid(obs)
        assert res.is_valid_candidate is True
        assert res.decision == "CANDIDATE_VERIFIED"
        assert res.status == "VERIFIED"
        assert res.canonical_name == "Sarah Chen"
        assert res.title == "Software Engineer"
        assert res.company == "Google"
        assert res.location == "San Francisco, CA"
        assert res.platform == "LinkedIn"
        assert res.canonical_profile_url == "https://www.linkedin.com/in/sarah-chen"
        assert res.quality_score >= 70
        assert res.identity_confidence >= 0.75

    # ─────────────────────────────────────────────────────────────
    # 5. Name-Only Extraction Rejected from Becoming Verified Candidate
    # ─────────────────────────────────────────────────────────────
    def test_name_alone_without_corroboration_rejected(self):
        """A name alone without profile URL or employment cannot become a verified candidate."""
        obs = {
            "name": "John Doe",
        }
        res = create_candidate_if_valid(obs)
        assert res.is_valid_candidate is False
        assert res.decision == "REJECTED_OBSERVATION"
        assert res.status == "REJECTED"

    # ─────────────────────────────────────────────────────────────
    # 6. Disallowed Context & Page Gating
    # ─────────────────────────────────────────────────────────────
    def test_disallowed_page_context_rejection(self):
        """Observations from INBOX or COMPANY_PAGE contexts are strictly disallowed."""
        obs = {
            "name": "Sarah Chen",
            "title": "Software Engineer",
            "company": "Google",
            "page_type": "INBOX",
        }
        res = create_candidate_if_valid(obs)
        assert res.is_valid_candidate is False
        assert res.decision == "REJECTED_OBSERVATION"
