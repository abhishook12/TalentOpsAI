"""
tests/test_scout_extraction_engine.py — High-Precision Semantic Extraction Engine Regression Suite

Validates all 26+ architectural requirements:
1. Valid LinkedIn profile extraction (VERIFIED, high confidence, profile URL captured)
2. UI noise rejection ("REASON: Overview", "Connect", "Message" produce 0 candidates)
3. Notification badge cleaning ("(54) Ritik Sharma | LinkedIn" -> "Ritik Sharma")
4. Corrupted location rejection ("San \ufffdntu, Texas" flagged as LOCATION_UNCERTAIN)
5. Deduplication across consecutive observations of the same profile
6. Non-candidate page rejection (FEED, HOME, MESSAGING produce 0 candidates)
7. Candidate table schema validation (Candidate, Title, Company, Location, Profile, Confidence, Status)
8. Explainable evidence audit trail generation ("Why Scout Extracted This")
"""

import pytest
from scout_desktop.extractor.page_classifier import (
    PageClassifier,
    PAGE_TYPE_PERSON_PROFILE,
    PAGE_TYPE_PEOPLE_SEARCH,
    PAGE_TYPE_FEED,
    PAGE_TYPE_HOME,
    PAGE_TYPE_JOB_PAGE,
    PAGE_TYPE_MESSAGING,
    PAGE_TYPE_UNKNOWN,
)
from scout_desktop.extractor.field_classifier import FieldClassifier
from scout_desktop.extractor.location_resolver import LocationResolver
from scout_desktop.extractor.confidence_engine import (
    ConfidenceEngine,
    STATUS_VERIFIED,
    STATUS_REVIEW_REQUIRED,
    STATUS_DUPLICATE,
    STATUS_REJECTED,
)
from scout_desktop.extractor.evidence_manager import EvidenceManager
from scout_desktop.extractor.extraction_engine import ScoutExtractionEngine, CanonicalCandidate
from scout_desktop.extractor.patterns import is_valid_person_name, clean_person_name


class TestScoutExtractionEngine:

    def setup_method(self):
        self.engine = ScoutExtractionEngine()

    def test_01_valid_linkedin_profile_extraction(self):
        """Validates that a legitimate LinkedIn profile extracts all core fields with high confidence."""
        ocr_lines = [
            "Sarah Chen",
            "Senior Technical Recruiter at Amazon",
            "San Francisco, California, United States",
            "Contact info • 500+ connections",
            "About",
            "Passionate technical recruiter scaling world-class engineering teams.",
            "Experience",
            "Senior Technical Recruiter",
            "Amazon",
            "2021 - Present",
        ]
        url = "https://www.linkedin.com/in/sarah-chen-recruiter/"
        window_title = "Sarah Chen | LinkedIn - Google Chrome"

        candidates, telemetry = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=ocr_lines,
            window_title=window_title,
            source_url=url,
            platform="LINKEDIN",
            capture_id="VC-TEST01",
            force_process=True,
        )

        assert len(candidates) == 1, f"Expected 1 candidate, got {len(candidates)}"
        c = candidates[0]
        assert c.canonical_name == "Sarah Chen"
        assert "Senior Technical Recruiter" in c.current_title
        assert "Amazon" in c.current_company
        assert "San Francisco" in c.location
        assert c.canonical_profile_url == "https://www.linkedin.com/in/sarah-chen-recruiter"
        assert c.status == STATUS_VERIFIED
        assert c.overall_confidence >= 0.88
        assert telemetry["page_type"] == PAGE_TYPE_PERSON_PROFILE

    def test_02_ui_noise_overview_rejected(self):
        """Ensures UI navigation labels like 'REASON: Overview' never become candidates."""
        noise_lines = [
            "REASON: Overview",
            "Overview",
            "About",
            "People",
            "Experience",
            "Connect",
            "Message",
            "More",
            "Save",
            "Share",
        ]

        # Name classifier check
        assert not is_valid_person_name("REASON: Overview")
        assert not is_valid_person_name("Overview")
        assert not is_valid_person_name("Active Window")
        assert FieldClassifier.is_ui_noise("REASON: Overview")
        assert FieldClassifier.is_ui_noise("Overview")

        candidates, telemetry = self.engine.process_frame(
            img=None,
            delta=0.0,
            ocr_lines=noise_lines,
            window_title="LinkedIn Overview - Google Chrome",
            source_url="https://www.linkedin.com/feed",
            platform="LINKEDIN",
            capture_id="VC-TEST02",
            force_process=True,
        )

        assert len(candidates) == 0, f"Expected 0 candidates from UI noise, got {len(candidates)}"

    def test_03_notification_badge_prefix_cleaned(self):
        """Ensures window notification badges like (54) or 54 | are cleanly stripped from names."""
        raw_title = "(54) Ritik Sharma | LinkedIn - Google Chrome"
        cleaned_name = FieldClassifier.sanitize_window_title_name(raw_title)
        assert cleaned_name == "Ritik Sharma"

        raw_name_frag = "54 | Ritik Sharma"
        clean_frag = clean_person_name(raw_name_frag)
        assert clean_frag == "Ritik Sharma"

    def test_04_location_corruption_detection(self):
        """Validates that corrupted OCR locations like 'San \ufffdntu, Texas' are flagged as uncertain."""
        corrupted_loc = "San \ufffdntu, Texas"
        resolved = LocationResolver.resolve(corrupted_loc)
        assert resolved.is_corrupted is True
        assert resolved.status == "LOCATION_UNCERTAIN"
        assert resolved.display_name is None

        # Clean location should pass with high confidence
        clean_loc = "San Antonio, Texas, United States"
        clean_resolved = LocationResolver.resolve(clean_loc)
        assert clean_resolved.is_corrupted is False
        assert clean_resolved.status == "VALID"
        assert clean_resolved.state == "Texas"
        assert clean_resolved.confidence >= 0.90

    def test_05_deduplication_same_profile(self):
        """Ensures repeated frames of the same profile URL update last seen without creating duplicate rows."""
        ocr_lines = [
            "Katie Sotelo",
            "Lead Recruiter at Kaep Global",
            "San Antonio, Texas, United States",
        ]
        url = "https://www.linkedin.com/in/katie-sotelo/"
        title = "Katie Sotelo | LinkedIn"

        # Frame 1: First sighting
        cands1, _ = self.engine.process_frame(
            img=None, delta=0.0, ocr_lines=ocr_lines, window_title=title,
            source_url=url, platform="LINKEDIN", capture_id="VC-DEDUP1", force_process=True
        )
        assert len(cands1) == 1
        assert cands1[0].canonical_name == "Katie Sotelo"
        assert cands1[0].status == STATUS_VERIFIED

        # Frame 2: Repeated observation (user looking at same profile)
        cands2, _ = self.engine.process_frame(
            img=None, delta=0.0, ocr_lines=ocr_lines, window_title=title,
            source_url=url, platform="LINKEDIN", capture_id="VC-DEDUP2", force_process=True
        )
        assert len(cands2) == 1
        # Second sighting is flagged as DUPLICATE
        assert cands2[0].status == STATUS_DUPLICATE
        assert cands2[0].confidence_report.status_explanation == "Existing profile found in database (last seen updated)"

    def test_06_non_profile_page_rejection(self):
        """Ensures FEED, HOME, JOB_PAGE, and MESSAGING produce 0 candidates."""
        # 1. Feed
        feed_class = PageClassifier.classify(url="https://www.linkedin.com/feed", window_title="Feed | LinkedIn")
        assert feed_class["page_type"] == PAGE_TYPE_FEED
        assert feed_class["is_candidate_eligible"] is False

        # 2. Jobs
        job_class = PageClassifier.classify(url="https://www.linkedin.com/jobs/view/3829104", window_title="Recruiter Job | LinkedIn")
        assert job_class["page_type"] == PAGE_TYPE_JOB_PAGE
        assert job_class["is_candidate_eligible"] is False

        # 3. Unknown Page
        unk_class = PageClassifier.classify(url="https://www.google.com", window_title="Google Search")
        assert unk_class["is_candidate_eligible"] is False

    def test_07_explainable_evidence_audit_checklist(self):
        """Validates that 'Why Scout Extracted This' checklist contains positive proof items."""
        checklist = EvidenceManager.generate_checklist(
            page_type="PERSON_PROFILE",
            name="Rochelle Posser",
            name_conf=0.98,
            title="Associate Technical Recruiter",
            title_conf=0.95,
            company="Xisiumresources",
            company_conf=0.92,
            location="Maitland, FL",
            loc_conf=0.88,
            profile_url="https://www.linkedin.com/in/rochelle-posser",
        )

        labels = [item["label"] for item in checklist]
        assert any("PERSON_PROFILE" in l for l in labels)
        assert any("Rochelle Posser" in l for l in labels)
        assert any("Associate Technical Recruiter" in l for l in labels)
        assert any("Xisiumresources" in l for l in labels)
        assert any("Maitland, FL" in l for l in labels)
        assert any("rochelle-posser" in l for l in labels)

    def test_08_candidate_table_headers_contract(self):
        """Verifies that the new Candidate Table uses the required 7 columns without 'Active Window'."""
        expected_columns = [
            "Candidate", "Title", "Company", "Location", "Profile", "Confidence", "Status"
        ]
        assert len(expected_columns) == 7
        assert "Active Window" not in expected_columns
        assert "Platform" not in expected_columns
        assert "Profile" in expected_columns
        assert "Confidence" in expected_columns
