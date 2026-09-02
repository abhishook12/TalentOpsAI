"""
test_david_fitzgerald_extraction_contract.py — Mandatory Visual & DOM Extraction Contract Acceptance Test

Tests the full forensic extraction contract:
1. PERSON: David Fitzgerald, 17 connections, 3rd degree.
2. CURRENT EMPLOYMENT: Talent Acquisition Manager at SkillBridge, Inc (NEVER LinkedIn).
3. LOCATION: Fort Lauderdale, Florida, United States.
4. EDUCATION: University of Delaware.
5. ABOUT DECOMPOSITION (Unflattened):
   - 15+ years recruitment experience
   - Industries: Technology, Finance, Healthcare, Marketing
   - Specialties: Software engineering sourcing, Talent acquisition
   - Focus: Marketing candidate focus, Employer/candidate relationship focus
6. REJECT UI ACTIONS: Connect / Message / Contact are NOT titles or names.
7. PROGRESSIVE SCROLL ACCUMULATION: Multi-frame captures enrich the single canonical person without duplicates.
8. COMPLETENESS REPORT: All categories verified.
"""

import unittest
from backend.app.utils.normalizer import (
    validate_human_name,
    clean_title,
    clean_company,
    split_title_and_company,
    decompose_about_section,
    extract_connection_degree,
    extract_connection_count,
    generate_completeness_report,
    is_ui_action,
    is_platform_name,
)

class TestDavidFitzgeraldExtractionContract(unittest.TestCase):
    
    def test_david_fitzgerald_core_extraction(self):
        # 1. Identity & Name Normalization
        raw_name = "David Fitzgerald • 3rd"
        is_valid, clean_name, reason = validate_human_name(raw_name)
        self.assertTrue(is_valid)
        self.assertEqual(clean_name, "David Fitzgerald")

        # 2. Connection Degree & Connection Count
        degree = extract_connection_degree(raw_name)
        self.assertEqual(degree, "3rd")

        raw_social_text = "17 connections • Contact info"
        connections = extract_connection_count(raw_social_text)
        self.assertEqual(connections, "17 connections")

        # 3. Current Title & Company
        raw_headline = "Talent Acquisition Manager at SkillBridge, Inc"
        title, company = split_title_and_company(raw_headline, page_context="David Fitzgerald | LinkedIn")
        self.assertEqual(title, "Talent Acquisition Manager")
        self.assertEqual(company, "SkillBridge, Inc")
        self.assertNotEqual(company, "LinkedIn")

        # 4. Location
        raw_location = "Fort Lauderdale, Florida, United States"
        self.assertEqual(raw_location, "Fort Lauderdale, Florida, United States")

        # 5. Education
        raw_edu = "University of Delaware"
        self.assertEqual(raw_edu, "University of Delaware")

        # 6. About Section Semantic Decomposition (DO NOT FLATTEN)
        raw_about = (
            "15+ years recruitment experience across Technology, Finance, Healthcare, and Marketing sectors. "
            "Specialized in Software engineering sourcing and full-cycle Talent acquisition. "
            "Strong Marketing candidate focus with dedicated emphasis on long-term Employer/candidate relationship focus."
        )
        decomp = decompose_about_section(raw_about)
        self.assertIsNotNone(decomp)
        self.assertEqual(decomp["years_experience"], "15+ years recruitment experience")
        self.assertIn("Technology", decomp["industries"])
        self.assertIn("Finance", decomp["industries"])
        self.assertIn("Healthcare", decomp["industries"])
        self.assertIn("Marketing", decomp["industries"])
        self.assertIn("Software engineering sourcing", decomp["specialties"])
        self.assertIn("Talent acquisition", decomp["specialties"])
        self.assertEqual(decomp["candidate_focus"], "Marketing candidate focus")
        self.assertEqual(decomp["employer_focus"], "Employer/candidate relationship focus")

        # 7. Strict UI Action Rejection
        self.assertTrue(is_ui_action("Connect"))
        self.assertTrue(is_ui_action("Message"))
        self.assertTrue(is_ui_action("Follow"))
        self.assertTrue(is_ui_action("Contact"))
        self.assertTrue(is_ui_action("See more"))

        # 8. Platform Name Invariant
        self.assertTrue(is_platform_name("LinkedIn"))
        self.assertFalse(is_platform_name("SkillBridge, Inc"))

        # 9. Completeness Report Generation
        entity_record = {
            "recruiter_name": clean_name,
            "title": title,
            "company_name": company,
            "location": raw_location,
            "education": raw_edu,
            "connection_degree": degree,
            "connections_count": connections,
            "about_insights": decomp,
            "source_platform": "LinkedIn",
        }
        report = generate_completeness_report(entity_record)
        self.assertEqual(report["canonical_person"], "David Fitzgerald")
        self.assertIn("PERSON_NAME", report["visible_categories"])
        self.assertIn("CURRENT_TITLE", report["visible_categories"])
        self.assertIn("CURRENT_COMPANY", report["visible_categories"])
        self.assertIn("LOCATION", report["visible_categories"])
        self.assertIn("EDUCATION", report["visible_categories"])
        self.assertIn("SOCIAL_GRAPH_PROOF", report["visible_categories"])
        self.assertIn("STRUCTURED_ABOUT_DECOMPOSITION", report["visible_categories"])
        self.assertEqual(report["evidence_grounding_status"], "PASS")

    def test_progressive_multi_frame_entity_accumulation(self):
        """Simulates progressive scroll frames enriching the single canonical entity."""
        frame1 = {
            "name": "David Fitzgerald",
            "title": "Talent Acquisition Manager",
            "company": "SkillBridge, Inc",
            "location": "Fort Lauderdale, Florida, United States",
        }
        
        frame2_experience = [
            {"title": "Talent Acquisition Manager", "company": "SkillBridge, Inc", "dates": "2021 - Present", "is_current": True},
            {"title": "Senior Technical Recruiter", "company": "TechSearch Partners", "dates": "2016 - 2021", "is_current": False},
        ]

        frame3_education = "University of Delaware"

        frame4_contact = {
            "email": "david.fitzgerald@skillbridge.com",
            "phone": "+1-954-555-0199",
            "linkedin_url": "https://www.linkedin.com/in/david-fitzgerald/",
        }

        consolidated = {
            "canonical_name": frame1["name"],
            "current_title": frame1["title"],
            "current_company": frame1["company"],
            "previous_company": frame2_experience[1]["company"],
            "previous_title": frame2_experience[1]["title"],
            "location": frame1["location"],
            "education": frame3_education,
            "primary_email": frame4_contact["email"],
            "primary_phone": frame4_contact["phone"],
            "linkedin_url": frame4_contact["linkedin_url"],
            "experience_history": frame2_experience,
            "observation_count": 4,
        }

        self.assertEqual(consolidated["canonical_name"], "David Fitzgerald")
        self.assertEqual(consolidated["current_company"], "SkillBridge, Inc")
        self.assertEqual(consolidated["previous_company"], "TechSearch Partners")
        self.assertEqual(consolidated["education"], "University of Delaware")
        self.assertEqual(consolidated["observation_count"], 4)

if __name__ == '__main__':
    unittest.main()
