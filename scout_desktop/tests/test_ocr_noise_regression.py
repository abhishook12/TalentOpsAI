import pytest
from scout_desktop.extractor.patterns import (
    is_valid_company_name,
    clean_company_name,
    is_valid_location,
    clean_location_text,
)

class TestCompanyValidationRegression:
    def test_consonant_cluster_corporations(self):
        corps = ["KPMG", "HSBC", "NYSE", "LVMH", "CBRE", "BNSF", "DTCC", "BBVA"]
        for c in corps:
            assert is_valid_company_name(c) is True, f"Failed: {c}"

    def test_corporate_suffixes_with_periods(self):
        corps = ["Stripe, Inc.", "Alphabet, Inc.", "Acme Corp.", "OpenAI, LLC.", "DeepMind Ltd."]
        for c in corps:
            cleaned = clean_company_name(c)
            assert cleaned is not None, f"clean failed: {c}"
            assert is_valid_company_name(cleaned) is True, f"valid failed: {cleaned}"

    def test_contact_preserving_companies(self):
        corps = ["Constant Contact", "Contact Solutions LLC", "Business Connections Inc"]
        for c in corps:
            cleaned = clean_company_name(c)
            assert "Contact" in cleaned or "Connections" in cleaned, f"stripped: {c}"
            assert is_valid_company_name(cleaned) is True, f"valid failed: {cleaned}"

    def test_advisory_and_consulting_firms(self):
        corps = ["Senior Advisor Group", "Cambridge Advisors", "Management Consultants Inc"]
        for c in corps:
            assert is_valid_company_name(c) is True, f"Failed: {c}"

    def test_companies_with_digits(self):
        corps = ["Level 3", "Factor 75", "8x8", "3M", "Studio 54"]
        for c in corps:
            assert is_valid_company_name(c) is True, f"Failed: {c}"

    def test_ocr_glyph_noise_rejected(self):
        noise_samples = ["IAou-(/p", "CotAMt fim any", "-(/p", "-5", "%iApps", "D,id", "San \ufffdntu\ufffd", "Active now"]
        for n in noise_samples:
            assert is_valid_company_name(n) is False, f"Accepted: {n}"

class TestLocationValidationRegression:
    def test_international_cities_with_diacritics(self):
        locations = ["Montréal, QC", "Montréal, Canada", "São Paulo, Brazil", "München, Germany", "Zürich, Switzerland", "Bogotá, Colombia"]
        for loc in locations:
            cleaned = clean_location_text(loc)
            assert cleaned is not None, f"clean returned None: {loc}"
            assert is_valid_location(cleaned) is True, f"is_valid failed: {cleaned}"

    def test_en_dash_metro_areas(self):
        locations = ["Dallas-Fort Worth, TX", "Dallas–Fort Worth, TX", "Winston-Salem, NC"]
        for loc in locations:
            cleaned = clean_location_text(loc)
            assert cleaned is not None
            assert "Fort Worth" in cleaned or "Salem" in cleaned, f"stripped: {cleaned}"
            assert is_valid_location(cleaned) is True, f"valid failed: {cleaned}"
