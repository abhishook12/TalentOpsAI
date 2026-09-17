import os
import json
import pytest
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
from scout_desktop.extractor.parsers import parse_with_modular_parsers

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "golden_dataset")


def load_fixture(filename: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


class TestGoldenDataset:
    """Automated regression tests across the permanent golden dataset."""

    def test_all_fixtures_exist(self):
        expected = [
            "linkedin_profile.json",
            "zoominfo_contact.json",
            "apollo_lead.json",
            "github_developer.json",
            "title_company_only.json",
            "cross_tab_mismatch.json",
            "noisy_chat_stream.json",
            "navigation_garbage.json",
        ]
        for fix in expected:
            assert os.path.exists(os.path.join(FIXTURES_DIR, fix)), f"Missing: {fix}"

    def test_linkedin_profile_golden_fixture(self):
        fix = load_fixture("linkedin_profile.json")
        ocr_text = "\n".join(fix["ocr_lines"])
        ctx = {"source_url": fix["source_url"], "window_title": fix["window_title"], "platform": fix["platform"]}
        parsed = parse_with_modular_parsers(ocr_text, ctx)
        assert parsed is not None
        assert parsed["recruiter_name"] == fix["expected_name"]
        assert parsed["company_name"] == fix["expected_company"]

        res = create_candidate_if_valid({
            "name": parsed["recruiter_name"],
            "title": parsed["title"],
            "company": parsed["company_name"],
            "location": parsed["location"],
            "canonical_profile_url": parsed["canonical_profile_url"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.is_valid_candidate is True
        assert res.status == "VERIFIED"
        assert res.reason_code == "PROFILE_URL_PRESENT"
        assert "name" in res.field_evidence
        assert "company" in res.field_evidence

    def test_zoominfo_contact_golden_fixture(self):
        fix = load_fixture("zoominfo_contact.json")
        ocr_text = "\n".join(fix["ocr_lines"])
        ctx = {"source_url": fix["source_url"], "window_title": fix["window_title"], "platform": fix["platform"]}
        parsed = parse_with_modular_parsers(ocr_text, ctx)
        assert parsed is not None
        assert parsed["recruiter_name"] == fix["expected_name"]
        assert parsed["email"] == fix["expected_email"]

        res = create_candidate_if_valid({
            "name": parsed["recruiter_name"],
            "title": parsed["title"],
            "company": parsed["company_name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.is_valid_candidate is True
        assert res.status == "VERIFIED"
        assert res.reason_code in ("VERIFIED_CONTACT_FOUND", "PROFILE_URL_PRESENT")
        assert "email" in res.field_evidence

    def test_apollo_lead_golden_fixture(self):
        fix = load_fixture("apollo_lead.json")
        ocr_text = "\n".join(fix["ocr_lines"])
        ctx = {"source_url": fix["source_url"], "window_title": fix["window_title"], "platform": fix["platform"]}
        parsed = parse_with_modular_parsers(ocr_text, ctx)
        assert parsed is not None
        assert parsed["recruiter_name"] == fix["expected_name"]
        assert parsed["email"] == fix["expected_email"]

        res = create_candidate_if_valid({
            "name": parsed["recruiter_name"],
            "title": parsed["title"],
            "company": parsed["company_name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.is_valid_candidate is True
        assert res.status == "VERIFIED"
        assert res.reason_code == "VERIFIED_CONTACT_FOUND"

    def test_github_developer_golden_fixture(self):
        fix = load_fixture("github_developer.json")
        ocr_text = "\n".join(fix["ocr_lines"])
        ctx = {"source_url": fix["source_url"], "window_title": fix["window_title"], "platform": fix["platform"]}
        parsed = parse_with_modular_parsers(ocr_text, ctx)
        assert parsed is not None
        assert parsed["recruiter_name"] == fix["expected_name"]

        res = create_candidate_if_valid({
            "name": parsed["recruiter_name"],
            "title": parsed["title"],
            "company": parsed["company_name"],
            "canonical_profile_url": parsed["canonical_profile_url"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.is_valid_candidate is True
        assert res.status == "VERIFIED"
        assert res.reason_code == "PROFILE_URL_PRESENT"

    def test_title_company_only_routing_to_review(self):
        """Title and company alone must be kept in REVIEW_REQUIRED."""
        fix = load_fixture("title_company_only.json")
        res = create_candidate_if_valid({
            "name": fix["expected_name"],
            "title": fix["expected_title"],
            "company": fix["expected_company"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.is_valid_candidate is False
        assert res.status == "REVIEW_REQUIRED"
        assert res.reason_code == "TITLE_COMPANY_ONLY"

    def test_cross_tab_mismatch_rejection(self):
        """Cross-tab slug mismatch must be rejected."""
        fix = load_fixture("cross_tab_mismatch.json")
        res = create_candidate_if_valid({
            "name": fix["expected_name"],
            "canonical_profile_url": fix["source_url"],
            "platform": fix["platform"],
            "window_title": fix["window_title"],
        })
        assert res.reason_code == "CROSS_TAB_MISMATCH" or any("CROSS_TAB_MISMATCH" in r for r in res.reasons)

    def test_navigation_garbage_rejection(self):
        """Navigation fragments and bad UI noise must be rejected as UNRESOLVED_UI_TEXT."""
        fix = load_fixture("navigation_garbage.json")
        for bad in fix["ocr_lines"]:
            res = create_candidate_if_valid({
                "name": bad,
                "platform": fix["platform"],
                "window_title": fix["window_title"],
            })
            assert res.is_valid_candidate is False
            assert res.status == "REJECTED"
