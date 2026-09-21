"""
Check 1: Desktop Scout Core Extraction & Pipeline Integrity Verification
Tests:
1. ScreenStabilityDetector immediate capture, window switch, settle behavior
2. PageClassifier eligibility across LinkedIn, Messaging, Jobright, ATS
3. CandidateGate handling of verified sourcing platforms with/without direct URL
4. Recruiter chat recommendation capture (REVIEW_REQUIRED)
5. Universal entity_extractor fallback for multi-candidate company cards
"""
import unittest
from PIL import Image
from scout_desktop.extractor.stability_detector import ScreenStabilityDetector
from scout_desktop.extractor.page_classifier import PageClassifier, PAGE_TYPE_PERSON_PROFILE, PAGE_TYPE_MESSAGING, PAGE_TYPE_JOB_PAGE
from scout_desktop.extractor.candidate_gate import create_candidate_if_valid
from scout_desktop.extractor.extraction_engine import ScoutExtractionEngine
from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.version import __version__


class TestScoutPipelineFixes(unittest.TestCase):

    def test_version_bump(self):
        self.assertEqual(__version__, "2.9.1")

    def test_stability_detector_immediate_and_switch(self):
        detector = ScreenStabilityDetector()
        img = Image.new('RGB', (100, 100), color='white')

        # Immediate capture / window switch (delta=1.0) MUST be STABLE_READY
        ready, state, _ = detector.update_frame(img, 1.0, "Michael Vos | LinkedIn - Google Chrome")
        self.assertTrue(ready, "Immediate capture delta=1.0 must be ready immediately")
        self.assertEqual(state, "STABLE_READY")

        # Force settle MUST be STABLE_READY
        ready, state, _ = detector.update_frame(img, 0.05, "Michael Vos | LinkedIn - Google Chrome", force_settle=True)
        self.assertTrue(ready)
        self.assertEqual(state, "STABLE_READY")

    def test_page_classifier_all_platforms(self):
        # 1. LinkedIn Profile
        res = PageClassifier.classify(url="https://www.linkedin.com/in/michael-vos", window_title="Michael Vos | LinkedIn", platform="LINKEDIN")
        self.assertTrue(res["is_candidate_eligible"])
        self.assertEqual(res["page_type"], PAGE_TYPE_PERSON_PROFILE)

        # 2. LinkedIn Profile with Empty URL (window title only)
        res = PageClassifier.classify(url="", window_title="Michael Vos | LinkedIn - Google Chrome", platform="LINKEDIN")
        self.assertTrue(res["is_candidate_eligible"])
        self.assertEqual(res["page_type"], PAGE_TYPE_PERSON_PROFILE)

        # 3. Google Chat Messaging (MUST be candidate eligible for candidate stream intelligence)
        res = PageClassifier.classify(url="https://chat.google.com/u/0/dm/123", window_title="Muskan Jain - Chat", platform="GOOGLE_CHAT")
        self.assertTrue(res["is_candidate_eligible"], "Chat messaging must be candidate eligible for recruiter streams")
        self.assertEqual(res["page_type"], PAGE_TYPE_MESSAGING)

        # 4. Jobright Sourcing Portal
        res = PageClassifier.classify(url="https://jobright.ai/jobs/12345", window_title="Lead Gen AI Developer @ Kodeva LLC", platform="JOBRIGHT")
        self.assertTrue(res["is_candidate_eligible"], "Jobright must be candidate eligible")

        # 5. Teams Messaging
        res = PageClassifier.classify(url="https://teams.microsoft.com/v2/", window_title="Chat | CTV- Phone numbers | Microsoft Teams", platform="TEAMS")
        self.assertTrue(res["is_candidate_eligible"], "Teams must be candidate eligible")

    def test_candidate_gate_linkedin_without_direct_url(self):
        # Candidate on LinkedIn where Chrome URL was not captured by UIA
        obs = {
            "recruiter_name": "Michael Vos",
            "title": "Senior Staff Software Engineer",
            "company_name": "Google",
            "location": "Mountain View, CA",
        }
        ctx = {
            "window_title": "Michael Vos | LinkedIn - Google Chrome",
            "source_url": "",
            "platform": "LINKEDIN",
        }
        gate_res = create_candidate_if_valid(obs, ctx)
        self.assertTrue(gate_res.is_valid_candidate, f"Should be valid candidate: {gate_res.reasons}")
        self.assertEqual(gate_res.decision, "CANDIDATE_VERIFIED")
        self.assertIn("linkedin.com", gate_res.canonical_profile_url)

    def test_candidate_gate_recruiter_chat_recommendation(self):
        # Recruiter in Google Chat shares a candidate recommendation
        obs = {
            "name": "Muskan Jain",
            "title": "Full Stack Developer",
            "company": "Infosys",
            "location": "Noida, India",
        }
        ctx = {
            "window_title": "Recruiter Channel - Chat",
            "source_url": "https://chat.google.com",
            "platform": "GOOGLE_CHAT",
            "page_type": "CHAT_RECRUITER_STREAM",
        }
        gate_res = create_candidate_if_valid(obs, ctx)
        self.assertIn(gate_res.decision, ("CANDIDATE_VERIFIED", "REVIEW_REQUIRED"))
        self.assertNotEqual(gate_res.decision, "REJECTED_OBSERVATION", "Recruiter chat candidate recommendation must not be rejected as noise")

    def test_universal_multi_card_fallback(self):
        # Multi-person directory (like SVK Systems Inc: People)
        lines = [
            "SVK Systems Inc: People | LinkedIn",
            "Employees at SVK Systems Inc",
            "John Doe",
            "Cloud Solutions Architect at SVK Systems Inc",
            "Hyderabad, India",
            "Connect",
            "Jane Smith",
            "Senior Talent Acquisition Specialist at SVK Systems Inc",
            "Dallas, TX",
            "Connect",
        ]
        extractor = EntityExtractor()
        clusters = extractor.extract_from_lines(
            lines=lines,
            capture_id="VC-TEST-001",
            source_url="https://www.linkedin.com/company/svk-systems/people",
            window_title="SVK Systems Inc: People | LinkedIn - Google Chrome",
            platform="LINKEDIN",
        )
        self.assertGreaterEqual(len(clusters), 1, "Should extract candidates from multi-person directory")


if __name__ == "__main__":
    unittest.main()
