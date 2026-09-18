import pytest
from scout_desktop.extractor.candidate_gate import (
    create_candidate_if_valid,
    is_individual_profile_url,
    is_url_slug_compatible_with_name,
)


class TestGateDecisionMatrix:
    def test_complete_candidate_verified(self):
        """Candidate with Name, Title, Company, and canonical profile URL must be VERIFIED."""
        obs = {
            "name": "Sarah Connor",
            "title": "Principal AI Engineer",
            "company": "Cyberdyne Systems",
            "location": "San Francisco, CA",
            "profile_url": "https://www.linkedin.com/in/sarah-connor-ai",
            "platform": "LinkedIn",
        }
        res = create_candidate_if_valid(obs)
        assert res.decision == "CANDIDATE_VERIFIED", f"Expected VERIFIED, got {res.decision} ({res.reasons})"
        assert res.is_valid_candidate is True
        assert res.canonical_name == "Sarah Connor"
        assert res.title == "Principal AI Engineer"
        assert res.company == "Cyberdyne Systems"

    def test_name_and_url_only_requires_professional_context(self):
        """A bare Name + URL with 0 title and 0 company cannot reach standard VERIFIED (rebalanced score)."""
        obs = {
            "name": "John Doe",
            "title": None,
            "company": None,
            "location": None,
            "profile_url": "https://www.linkedin.com/in/johndoe",
            "platform": "LinkedIn",
        }
        res = create_candidate_if_valid(obs)
        # Quality score = 25 (name) + 30 (URL) = 55 (below 70 verified threshold)
        assert res.decision == "REVIEW_REQUIRED", f"Expected REVIEW_REQUIRED, got {res.decision}"
        assert res.quality_score < 70

    def test_corrupted_company_routes_to_review(self):
        """Candidate with OCR-corrupted company must be held in REVIEW_REQUIRED."""
        obs = {
            "name": "Danielle Tocco",
            "title": "Staff Recruiter",
            "company": "IAou-(/p",
            "location": "San Francisco, CA",
            "profile_url": "https://www.linkedin.com/in/danielle-tocco",
            "platform": "LinkedIn",
        }
        res = create_candidate_if_valid(obs)
        assert res.decision == "REVIEW_REQUIRED"
        assert res.company is None
        assert any("CORRUPTED_COMPANY_REJECTED" in r for r in res.reasons)

    def test_subdomain_email_derives_correct_company(self):
        """Corporate email like jane@hr.meta.com must derive 'Meta', not 'Hr'."""
        obs = {
            "name": "Jane Smith",
            "title": "Talent Partner",
            "company": None,
            "email": "jane@hr.meta.com",
            "profile_url": "https://www.linkedin.com/in/janesmith",
            "platform": "LinkedIn",
        }
        res = create_candidate_if_valid(obs)
        assert res.company == "Meta", f"Expected 'Meta', got '{res.company}'"

    def test_bad_ui_noise_strings_rejected(self):
        """Garbage and UI fragments must be REJECTED_OBSERVATION."""
        noise_names = ["355 M Inbox (121)", "54 Ri Ht...", "iHHI", "My", "Active window", "REASON: Overview"]
        for bad_name in noise_names:
            obs = {"name": bad_name, "platform": "LinkedIn"}
            res = create_candidate_if_valid(obs)
            assert res.decision in ("REJECTED_OBSERVATION", "UNRESOLVED_UI_TEXT"), f"Failed on {bad_name}: {res.decision}"
