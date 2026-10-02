"""
Unit test suite for DesktopEntityTypeClassifier in scout_desktop.
Tests deterministic gate separation across:
- PERSON
- COMPANY
- JOB_POSTING
- CONTACT_INFO
- MARKET_SIGNAL
- NOISE
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scout_desktop.extractor.entity_classifier import (
    desktop_entity_classifier,
    ENTITY_PERSON,
    ENTITY_COMPANY,
    ENTITY_JOB_POSTING,
    ENTITY_CONTACT_INFO,
    ENTITY_MARKET_SIGNAL,
    ENTITY_NOISE,
)


class TestDesktopEntityTypeClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = desktop_entity_classifier

    def test_person_classification(self):
        cases = [
            ("Sarah Chen", "Staff Software Engineer", "Stripe"),
            ("Marcus Webb", "Head of Talent", "Airbnb"),
            ("Danielle Mason", "Lead Technical Recruiter", "Datadog"),
            ("Priya Nair", "Director of Engineering", "Meta"),
            ("David Miller", "VP Engineering", "Google"),
        ]
        for name, title, comp in cases:
            res = self.classifier.classify(raw_name=name, raw_title=title, raw_company=comp)
            self.assertEqual(
                res["entity_type"], ENTITY_PERSON,
                f"Expected PERSON for {name}, got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.70)

    def test_company_classification(self):
        cases = [
            {"raw_name": "Helix Labs Corp", "raw_title": "Biotechnology", "raw_company": "Helix Labs Corp"},
            {"raw_name": "Acme Technologies LLC", "raw_title": "Computer Software", "raw_company": ""},
            {"raw_name": "Stripe", "raw_title": "Financial Services", "source_url": "https://www.linkedin.com/company/stripe"},
            {"raw_name": "Beacon Tech Inc", "raw_title": "Staffing and Recruiting", "raw_email": "info@beacontech.com"},
            {"raw_name": "Apex Staffing Solutions", "raw_title": "Information Technology", "raw_company": "Apex Staffing Solutions"},
        ]
        for c in cases:
            res = self.classifier.classify(**c)
            self.assertEqual(
                res["entity_type"], ENTITY_COMPANY,
                f"Expected COMPANY for {c['raw_name']}, got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.40)

    def test_job_posting_classification(self):
        cases = [
            {"raw_name": "Senior Full Stack Engineer", "raw_title": "Full-time · Remote", "raw_company": "Netflix"},
            {"raw_name": "Transmission Project Manager", "raw_title": "Contract", "raw_company": "NextEra Energy"},
            {"raw_name": "High School Mathematics Teacher", "raw_title": "Austin, TX", "raw_company": "Austin ISD"},
            {"raw_name": "Now Hiring: Staff DevOps Architect", "raw_title": "Full-time", "raw_company": "Uber"},
            {"raw_name": "Senior Software Engineer", "source_url": "https://www.linkedin.com/jobs/view/123456789"},
        ]
        for c in cases:
            res = self.classifier.classify(**c)
            self.assertEqual(
                res["entity_type"], ENTITY_JOB_POSTING,
                f"Expected JOB_POSTING for {c['raw_name']}, got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.40)

    def test_contact_info_classification(self):
        cases = [
            {"raw_name": "Contact Us", "raw_email": "support@company.com", "raw_phone": "+1-800-555-0199"},
            {"raw_name": "General Inquiries", "raw_email": "info@startup.io"},
            {"raw_name": "Customer Support", "raw_phone": "1-888-123-4567", "source_url": "https://company.com/contact"},
            {"raw_name": "Help Desk", "raw_email": "helpdesk@enterprise.org"},
        ]
        for c in cases:
            res = self.classifier.classify(**c)
            self.assertEqual(
                res["entity_type"], ENTITY_CONTACT_INFO,
                f"Expected CONTACT_INFO for {c['raw_name']}, got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.40)

    def test_market_signal_classification(self):
        cases = [
            {"raw_name": "Tech Hiring Surge in Q3 2026", "raw_title": "Market Trends", "raw_company": ""},
            {"raw_name": "Restructuring and Layoffs Report", "raw_title": "Industry Analysis", "source_page_title": "TechCrunch News"},
            {"raw_name": "Annual Workforce Salary Guide 2026", "raw_title": "Compensation Report", "raw_company": ""},
        ]
        for c in cases:
            res = self.classifier.classify(**c)
            self.assertEqual(
                res["entity_type"], ENTITY_MARKET_SIGNAL,
                f"Expected MARKET_SIGNAL for {c['raw_name']}, got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.40)

    def test_noise_classification(self):
        cases = [
            {"raw_name": "Sign in to continue", "raw_title": "", "raw_company": ""},
            {"raw_name": "See all 14 results", "raw_title": "", "raw_company": ""},
            {"raw_name": "4 new notifications", "raw_title": "", "raw_company": ""},
            {"raw_name": "Cookie Preferences", "raw_title": "", "raw_company": ""},
            {"raw_name": "LinkedIn", "raw_title": "", "raw_company": ""},
            {"raw_name": "", "raw_title": "", "raw_company": ""},
        ]
        for c in cases:
            res = self.classifier.classify(**c)
            self.assertEqual(
                res["entity_type"], ENTITY_NOISE,
                f"Expected NOISE for '{c['raw_name']}', got {res['entity_type']} (reason: {res.get('reason')})"
            )
            self.assertGreaterEqual(res["confidence"], 0.60)


if __name__ == "__main__":
    unittest.main()
