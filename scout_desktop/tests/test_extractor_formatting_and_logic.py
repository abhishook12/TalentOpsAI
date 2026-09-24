"""
tests/test_extractor_formatting_and_logic.py — Regression Test for Title, Company, and OCR Sanitization.

Guards:
1. Title cleaning (stripping leading dashes, bullets, numbers, degrees: '- Recruiter I' -> 'Recruiter I').
2. OCR error repair (e.g. 'Partners Ihited' -> 'Partners Limited', 'TechnoIogies' -> 'Technologies').
3. Multi-segment headline extraction in clean_title_and_company ('- Recruiter I · Partners Ihited' -> 'Recruiter I', 'Partners Limited').
4. Candidate creation gate title/company sanitization and chat partner exclusion.
"""

import pytest
from scout_desktop.extractor.patterns import (
    clean_job_title,
    clean_company_name,
    clean_title_and_company,
    is_plausible_title,
    is_valid_company_name,
)
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid


class TestExtractorFormattingAndLogic:
    """Verifies that titles, companies, and headlines are logically parsed and sanitized."""

    @pytest.mark.parametrize(
        "raw_title, expected_clean",
        [
            ("- Recruiter I", "Recruiter I"),
            ("– Technical Recruiter", "Technical Recruiter"),
            ("— Senior Sourcer", "Senior Sourcer"),
            ("• Talent Partner · 1st", "Talent Partner"),
            ("· Recruiter II", "Recruiter II"),
            ("Talent Partner (2nd degree)", "Talent Partner"),
            ("Lead Architect (he/him)", "Lead Architect"),
            ("| Director of Operations /", "Director of Operations"),
            ("1. Staff Software Engineer", "Staff Software Engineer"),
            ("1) Engineering Manager - ", "Engineering Manager"),
            ("Director of Talent (office)", "Director of Talent"),
            ("  - Recruiter  ", "Recruiter"),
        ],
    )
    def test_clean_job_title_sanitizes_bullets_and_punctuation(self, raw_title, expected_clean):
        """Job titles must never retain leading/trailing dashes, bullets, numbers, or tags."""
        result = clean_job_title(raw_title)
        assert result == expected_clean

    @pytest.mark.parametrize(
        "raw_company, expected_clean",
        [
            ("Partners Ihited", "Partners Limited"),
            ("Partners lhited", "Partners Limited"),
            ("Acme TechnoIogies", "Acme Technologies"),
            ("Global SoIutions", "Global Solutions"),
            ("Apex ServIces", "Apex Services"),
            ("United HoIdings", "United Holdings"),
            ("Acme C0.", "Acme Co."),
            ("Omicron Pvt 1td", "Omicron Pvt Ltd"),
            ("- Google LLC", "Google LLC"),
            ("• Meta", "Meta"),
        ],
    )
    def test_clean_company_name_repairs_ocr_artifacts(self, raw_company, expected_clean):
        """Company names must repair narrow-font OCR degradations and strip leading bullets."""
        result = clean_company_name(raw_company)
        assert result == expected_clean

    def test_clean_title_and_company_decomposes_bullet_headline(self):
        """Headlines with bullet or dash separators must cleanly factorize into title and company."""
        headline = "- Recruiter I · Partners Ihited"
        title, company = clean_title_and_company(headline)
        assert title == "Recruiter I"
        assert company == "Partners Limited"

    def test_clean_title_and_company_decomposes_standard_headlines(self):
        """Standard '@' and 'at' headlines must be cleanly parsed and sanitized."""
        t1, c1 = clean_title_and_company("- Senior Talent Partner @ Cyberdyne Systems | AI")
        assert t1 == "Senior Talent Partner"
        assert c1 == "Cyberdyne Systems"

        t2, c2 = clean_title_and_company("Staff Recruiter at Stripe · 1st")
        assert t2 == "Staff Recruiter"
        assert c2 == "Stripe"

    def test_candidate_gate_sanitizes_raw_title_and_company(self):
        """Candidate creation gate must output sanitized title and company even if raw was dirty."""
        obs = {
            "name": "Tushar Pal",
            "title": "- Recruiter I",
            "company": "Partners Ihited",
            "source_url": "https://www.linkedin.com/in/tusharpal",
        }
        res = create_candidate_if_valid(obs)
        assert res.title == "Recruiter I"
        assert res.company == "Partners Limited"

    def test_chat_partner_channel_exclusion_with_pipes(self):
        """Chat window title with pipes e.g. 'Gaurav Dwivedi | Technovion - Chat' excludes conversation partner."""
        obs = {
            "name": "Gaurav Dwivedi",
            "title": "Recruiter I",
            "company": "Partners Limited",
            "window_title": "Gaurav Dwivedi | Technovion - Chat - Google Chrome",
        }
        res = create_candidate_if_valid(obs)
        assert res.is_valid_candidate is False
        assert res.decision == "REJECTED_OBSERVATION"
        assert "chat conversation partner" in res.reasons[0]
