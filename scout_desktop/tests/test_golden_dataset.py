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

    @pytest.mark.parametrize("headline, role, company", [
        ("Engineering Manager＠Myntra｜EX OLA", "Engineering Manager", "Myntra"),
        ("Senior Recruiter at Acme Corp", "Senior Recruiter", "Acme Corp"),
        ("Product Designer@Adobe I EX Example", "Product Designer", "Adobe"),
        ("Headhunter at Amundson Group", "Headhunter", "Amundson Group"),
        ("Staffing Professional at Kelly Services", "Staffing Professional", "Kelly Services"),
    ])
    def test_explicit_employment_across_layouts(self, headline, role, company):
        from scout_desktop.extractor.patterns import explicit_employment
        assert explicit_employment(headline) == (role, company)
        assert explicit_employment("contact@example.com") is None

    def test_contact_table_keeps_people_and_empty_cells_separate(self):
        from scout_desktop.extractor.contact_table import extract_contact_table
        rows = ["Company\tFull Name\tTitle", "Acme Corp\tMorgan Reed\t",
                "\tJordan Hayes\tSenior Recruiter", "Adobe\tshifted\textra\tcells"]
        people = extract_contact_table(rows, "fixture", "")
        assert [(p.canonical_name, p.current_company, p.current_title) for p in people] == [
            ("Morgan Reed", "Acme Corp", None), ("Jordan Hayes", None, "Senior Recruiter")]

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
        assert parsed["title"] == fix["expected_title"]
        assert parsed["location"] == fix["expected_location"]

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


    def test_banner_noise_does_not_override_headline_company(self):
        """OCR garbage from banner images must not replace the headline employer."""
        ocr_text = "\n".join([
            "CONSTRUCTION",
            "HEADHUNTING",
            "EXPERTS",
            "orotile TOI",
            "Yvonne Humphries",
            "Headhunter at Amundson Group",
            "Houston, Texas, United Yates · Contact info",
            "15,182 followers",
            "500+ connections",
            "Message",
            "Pending",
            "Amundson Group",
            "Texas State University",
        ])
        parsed = parse_with_modular_parsers(ocr_text, {
            "source_url": "https://linkedin.com/in/yvonnehumphries/",
            "window_title": "Yvonne Humphries | LinkedIn",
            "platform": "LinkedIn",
        })
        assert parsed is not None
        assert parsed["recruiter_name"] == "Yvonne Humphries"
        assert parsed["title"] == "Headhunter"
        assert parsed["company_name"] == "Amundson Group"
        assert parsed["location"] == "Houston, Texas, United States"

    def test_linkedin_affiliation_rail_preserves_bare_employer_and_school(self):
        """A visible employer beside a school must not be discarded as a person name."""
        ocr_text = "\n".join([
            "Katie Malone",
            "Principal Technology Consultant | ERP / MES / PLM",
            "Cork, County Cork, Ireland",
            "Morgan McKinley",
            "University College Cork",
            "About",
            "ERP and technology recruitment specialist.",
        ])
        parsed = parse_with_modular_parsers(ocr_text, {
            "source_url": "https://www.linkedin.com/in/katie-malone-049410189/",
            "window_title": "Katie Malone | LinkedIn",
            "platform": "LinkedIn",
        })
        assert parsed is not None
        assert parsed["company_name"] == "Morgan McKinley"
        assert parsed["education"] == "University College Cork"
        assert parsed["location"] == "Cork, County Cork, Ireland"

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
