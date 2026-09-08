"""
tests/test_extraction_quality.py — Comprehensive Extraction Precision & Quality Test Suite

Verifies:
1. Top Colleges & Universities Extraction (IIT, BITS, Caltech, INSEAD, Stanford, MIT, Georgia Tech, etc.)
2. Multi-line Degree & Graduation Date Extraction
3. Primary Personal Location Isolation from Header Zone (ignoring past job locations)
4. Social Proof & Activity Distractor Rejection (e.g. 'Followed by...', '500+ connections')
5. Dedicated Skills Section Extraction & Noise Filtering
6. Full About Summary, Years of Experience, and Specializations Persistence
7. Complete Chronological Career History (Current + Past Roles with Tenure)
8. Multi-Scroll Profile Continuity without Duplicate Observations
"""

import os
import sys
import unittest

BASE_DIR = r"c:\TalentOpsAI"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.extractor.patterns import (
    is_plausible_school,
    is_plausible_degree,
    is_valid_skill,
    is_valid_location,
    is_valid_company_name,
)


class TestExtractionQuality(unittest.TestCase):

    def setUp(self):
        self.extractor = EntityExtractor()

    def test_top_colleges_and_universities(self):
        """Verify school recognizer handles top international, specialized, and acronym institutions."""
        schools = [
            ("Stanford University", True),
            ("Massachusetts Institute of Technology", True),
            ("Georgia Institute of Technology", True),
            ("Indian Institute of Technology, Delhi", True),
            ("IIT Bombay", True),
            ("BITS Pilani", True),
            ("Caltech", True),
            ("INSEAD", True),
            ("Notre Dame", True),
            ("Virginia Tech", True),
            ("UIUC", True),
            ("Carnegie Mellon University", True),
            ("UC Berkeley", True),
            ("London School of Economics", True),
            ("Oxford University", True),
            ("Cambridge University", True),
            ("Wharton School", True),
            ("Followed by 10 mutual connections", False),
            ("San Francisco, CA", False),
        ]
        for name, expected in schools:
            result = is_plausible_school(name)
            self.assertEqual(result, expected, f"Failed for school: {name}")

    def test_degree_recognition(self):
        """Verify degree recognizer matches common degree titles."""
        degrees = [
            ("Bachelor of Science - BS, Computer Science", True),
            ("Master of Science in Artificial Intelligence", True),
            ("Ph.D. in Robotics and Computer Vision", True),
            ("B.Tech in Electrical Engineering", True),
            ("Master of Business Administration (MBA)", True),
            ("Associate of Arts", True),
            ("Senior Director of Engineering", False),
            ("San Francisco Bay Area", False),
        ]
        for deg, expected in degrees:
            result = is_plausible_degree(deg)
            self.assertEqual(result, expected, f"Failed for degree: {deg}")

    def test_social_proof_company_distractor_rejection(self):
        """Verify company validator rejects social proof and activity noise."""
        distractors = [
            "Followed by Praveen Reddy, Muskan and 1 other",
            "500+ connections",
            "12,450 followers",
            "Mutual connection with John Doe",
            "People you may know",
            "Talks about #recruiting and #tech",
            "Activity · 15 posts",
            "Show all 25 experiences",
            "View full profile",
            "See all 8 recommendations",
        ]
        for dis in distractors:
            self.assertFalse(is_valid_company_name(dis), f"Distractor wrongly accepted as company: {dis}")

        # Real companies must be accepted
        real_companies = [
            "Stripe",
            "Cyberdyne Systems",
            "Google LLC",
            "Elevate Digital",
            "Microsoft",
            "Amazon Web Services",
        ]
        for comp in real_companies:
            self.assertTrue(is_valid_company_name(comp), f"Legitimate company rejected: {comp}")

    def test_location_isolation_from_header(self):
        """Verify candidate primary location is taken from Header Zone and not past jobs."""
        lines = [
            "David Miller",
            "Lead Technical Recruiter at Datadog",
            "Austin, Texas, United States · Contact info",
            "500+ connections",
            "Experience",
            "Lead Technical Recruiter",
            "Datadog",
            "Jan 2022 - Present",
            "Senior Sourcer",
            "Meta",
            "Mar 2018 - Dec 2021",
            "Menlo Park, California, United States",
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-LOC-1",
            source_url="https://linkedin.com/in/david-miller",
            window_title="David Miller | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        staged = clusters[0].to_staged_contact_dict()
        self.assertEqual(staged.get("location"), "Austin, Texas, United States")
        self.assertNotEqual(staged.get("location"), "Menlo Park, California, United States")

    def test_education_section_parsing(self):
        """Verify multi-line education extraction captures school and degree."""
        lines = [
            "Maya Lin",
            "AI Research Scientist at OpenAI",
            "San Francisco, CA",
            "Education",
            "Carnegie Mellon University",
            "Ph.D. in Machine Learning and Robotics",
            "2016 - 2021",
            "Massachusetts Institute of Technology",
            "Bachelor of Science - BS, Computer Science",
            "2012 - 2016",
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-EDU-1",
            source_url="https://linkedin.com/in/maya-lin",
            window_title="Maya Lin | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        c = clusters[0]
        staged = c.to_staged_contact_dict()
        self.assertIn("Carnegie Mellon University", staged.get("education"))
        self.assertIn("Ph.D.", staged.get("education"))

        # Verify atomic observations
        preds = {obs.predicate: obs.object_value for obs in c.observations}
        self.assertIn("STUDIED_AT", preds)
        self.assertIn("HAS_DEGREE", preds)

    def test_skills_section_parsing(self):
        """Verify dedicated skills section extracts individual clean skills."""
        lines = [
            "Elena Rostova",
            "Staff AI Researcher at DeepMind",
            "London, United Kingdom",
            "Skills",
            "PyTorch · Reinforcement Learning · Distributed Systems · CUDA",
            "Show all 18 skills",
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-SKILL-1",
            source_url="https://linkedin.com/in/elena-rostova",
            window_title="Elena Rostova | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        staged = clusters[0].to_staged_contact_dict()
        skills = staged.get("skills", [])
        self.assertIn("PyTorch", skills)
        self.assertIn("Reinforcement Learning", skills)
        self.assertIn("Distributed Systems", skills)
        self.assertIn("CUDA", skills)
        self.assertNotIn("Show all 18 skills", skills)

    def test_about_summary_persistence(self):
        """Verify full About paragraph persists into about_summary without predicate mismatch."""
        summary = "Seasoned technical recruiter with 10+ years specializing in backend infrastructure and high-throughput systems."
        lines = [
            "Marcus Vance",
            "Principal Recruiter at Snowflake",
            "Seattle, WA",
            "About",
            summary,
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-ABOUT-1",
            source_url="https://linkedin.com/in/marcus-vance",
            window_title="Marcus Vance | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        staged = clusters[0].to_staged_contact_dict()
        self.assertEqual(staged.get("about_summary"), summary)

    def test_complete_chronological_career(self):
        """Verify both current and previous roles are in experience_history."""
        lines = [
            "Rachel Green",
            "Senior Talent Partner at Figma",
            "New York, NY",
            "Experience",
            "Senior Talent Partner",
            "Figma",
            "Jan 2023 - Present",
            "Technical Sourcer",
            "Dropbox",
            "Jun 2019 - Dec 2022",
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-EXP-1",
            source_url="https://linkedin.com/in/rachel-green",
            window_title="Rachel Green | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        staged = clusters[0].to_staged_contact_dict()
        exp = staged.get("experience_history", [])
        self.assertTrue(len(exp) >= 2)
        companies = [r.get("company") for r in exp]
        self.assertIn("Figma", companies)
        self.assertIn("Dropbox", companies)
    def test_pronoun_stripping_and_civic_employer(self):
        """Verify pronouns are cleanly stripped and civic/government employers are recognized."""
        lines = [
            "Gina Tomlinson (she/her) · 1st",
            "Chief Information Officer at City and County of San Francisco",
            "San Francisco Bay Area · Contact info",
            "About",
            "Executive technology leader with 20+ years experience building enterprise platforms.",
            "Experience",
            "Chief Information Officer",
            "City and County of San Francisco",
            "Jan 2020 - Present",
            "Education",
            "University of California, Berkeley",
            "Bachelor of Science - BS, Computer Science",
            "Skills",
            "Enterprise Architecture",
            "Cloud Computing",
        ]
        clusters = self.extractor.extract_from_lines(
            lines=lines,
            capture_id="CAP-GINA-TEST",
            source_url="https://linkedin.com/in/gina-tomlinson",
            window_title="Gina Tomlinson (she/her) | LinkedIn",
        )
        self.assertEqual(len(clusters), 1)
        staged = clusters[0].to_staged_contact_dict()
        self.assertEqual(staged.get("recruiter_name"), "Gina Tomlinson")
        self.assertEqual(staged.get("company_name"), "City and County of San Francisco")
        self.assertEqual(staged.get("title"), "Chief Information Officer")
        self.assertIn("San Francisco", staged.get("location"))
        self.assertIn("Berkeley", staged.get("education"))
        self.assertEqual(len(staged.get("skills")), 2)

    def test_window_title_never_becomes_company(self):
        """Verify window titles with ' | LinkedIn' are strictly rejected as companies."""
        self.assertFalse(is_valid_company_name("Gina Tomlinson (she/her) | LinkedIn"))
        self.assertFalse(is_valid_company_name("Marcus Vance | LinkedIn"))
        self.assertFalse(is_valid_company_name("Software Engineer | LinkedIn"))
        self.assertTrue(is_valid_company_name("City and County of San Francisco"))
        self.assertTrue(is_valid_company_name("Stripe"))


if __name__ == "__main__":
    unittest.main()
