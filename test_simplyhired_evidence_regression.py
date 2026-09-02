"""
SimplyHired Job Search Screen & Evidence Grounding Regression Test Suite.
Verifies that:
1. Job titles (e.g. 'High School Mathematics Teacher', 'Transmission Project Manager') are NEVER person names.
2. Job platform 'SimplyHired' is NEVER an employer company.
3. Job Search pages do NOT invent fake person candidates.
4. The Evidence Grounding Gate hard-rejects ungrounded records into 'rejected' staging status without touching master DB.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.utils.normalizer import (
    classify_page_type,
    validate_human_name,
    is_job_posting_title,
    is_platform_name,
    is_ui_action,
    clean_title,
    clean_company,
    evaluate_evidence_grounding,
    calculate_field_confidences,
)
from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.services.discovery_processor import DiscoveryProcessor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestSimplyHiredEvidenceRegression(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.user = User(
            id=1,
            email="abhishekjadon824@gmail.com",
            first_name="Abhishek",
            last_name="Jadon",
            status="Active"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_job_search_page_classification(self):
        """1. Page type must be JOB_SEARCH_PAGE."""
        pt = classify_page_type("https://www.simplyhired.com/search?q=project+manager", "SimplyHired - Jobs")
        self.assertEqual(pt, "JOB_SEARCH_PAGE")

    def test_job_title_rejection_as_person(self):
        """2. Job posting titles must be rejected from being human names."""
        bad_names = [
            "High School Mathematics Teacher",
            "Transmission Project Manager",
            "Mobile Phlebotomist",
            "Senior ServiceNow Developer - Certified",
            "Specimen Collector",
            "Order Management Cloud Specialist",
            "Professional Lead",
            "Candidate Lead"
        ]

        for title in bad_names:
            self.assertTrue(is_job_posting_title(title) or title in {"Professional Lead", "Candidate Lead"}, f"'{title}' must be recognized as job posting title or placeholder")
            valid, clean, reason = validate_human_name(title)
            self.assertFalse(valid, f"'{title}' must NOT be accepted as a human person name")

    def test_simplyhired_platform_exclusion(self):
        """3. 'simplyhired' must be recognized as platform, never employer."""
        self.assertTrue(is_platform_name("simplyhired"))
        self.assertTrue(is_platform_name("SimplyHired"))
        self.assertIsNone(clean_company("simplyhired"))
        self.assertEqual(clean_company("simplyhired", "Metasys Technologies Inc."), "Metasys Technologies Inc.")

    def test_evidence_grounding_evaluation(self):
        """4. Bad SimplyHired extraction must fail Evidence Grounding Check."""
        grounding = evaluate_evidence_grounding(
            raw_name="High School Mathematics Teacher",
            raw_title="Professional Lead",
            raw_company="simplyhired",
            page_url="https://www.simplyhired.com/search?q=project+manager",
            page_title="Jobs in Las Vegas, NV | SimplyHired"
        )

        self.assertFalse(grounding["is_grounded"], "Ungrounded extraction must fail grounding check")
        self.assertEqual(grounding["grounding_score"], 0)
        self.assertEqual(grounding["decision"], "REJECT_UNGROUNDED")
        self.assertGreaterEqual(len(grounding["rejection_reasons"]), 2)

    def test_staging_gate_blocks_master_db_corruption(self):
        """5. Batch Processor must reject ungrounded record and protect Master DB."""
        stg = DiscoveryStaging(
            batch_id="BATCH-TEST-SH",
            discovery_id="DISC-4D158385",
            device_id="VC-61680",
            owner_user_id=1,
            raw_name="High School Mathematics Teacher",
            raw_title="Professional Lead",
            raw_company="simplyhired",
            source_url="https://www.simplyhired.com/search?q=project+manager",
            source_page_title="Jobs in Las Vegas, NV | SimplyHired",
            capture_id="VC-61680",
            extraction_source="visual_capture",
            processing_status="pending",
        )
        self.db.add(stg)
        self.db.commit()

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_pending_batch()

        # Check stats
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["rejected"], 1, "Must reject ungrounded record")
        self.assertEqual(stats["new"], 0, "Must NOT create any new master recruiter")

        # Check staging record state
        staged_check = self.db.query(DiscoveryStaging).filter(DiscoveryStaging.discovery_id == "DISC-4D158385").first()
        self.assertEqual(staged_check.processing_status, "rejected")
        self.assertEqual(staged_check.decision, "REJECT_UNGROUNDED")
        self.assertIn("Name validation failed", staged_check.decision_reason)
        self.assertEqual(staged_check.identity_confidence, 0.0)

        # Master DB checks: MUST BE EMPTY!
        rec_count = self.db.query(Recruiter).count()
        comp_count = self.db.query(Company).count()
        resolved_count = self.db.query(ResolvedPerson).count()

        self.assertEqual(rec_count, 0, "Master Recruiter DB must remain 0")
        self.assertEqual(comp_count, 0, "Master Company DB must remain 0")
        self.assertEqual(resolved_count, 0, "Silver ResolvedPerson DB must remain 0")

        print("\n>>> SIMPLYHIRED EVIDENCE GROUNDING REGRESSION SUITE: ALL ASSERTIONS PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
