"""
Progressive Profile & Active Entity Lock Regression Test Suite.
Verifies that:
1. Scrolling down a single profile accumulates information into ONE single person record.
2. Current company ('Premier Staffing Solution LLC') is NEVER overwritten by previous company ('ABC Staffing').
3. Small metadata (location, education, followers, connections, about) is preserved.
4. Exactly 1 master recruiter is created from 4 sequential scroll observations.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.services.discovery_processor import DiscoveryProcessor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestProgressiveProfileRegression(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.user = User(
            id=1,
            email="recruiter-lead@talentops.ai",
            first_name="Talent",
            last_name="Scout",
            status="Active"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_kelsei_martinez_progressive_scroll_enrichment(self):
        """
        Simulates 4 sequential scroll captures of Kelsei Martinez's LinkedIn profile.
        Verifies that:
        - All 4 frames merge into 1 ResolvedPerson
        - Current company is Premier Staffing Solution LLC
        - Previous company is ABC Staffing
        - Location, education, followers, connections, and about are extracted and preserved.
        """
        profile_url = "https://www.linkedin.com/in/kelseirobertson/"

        # Observation 1: Top Card Viewport (VC-701)
        stg1 = DiscoveryStaging(
            batch_id="BATCH-KELSEI-PROG",
            discovery_id="DISC-KELSEI-01",
            device_id="VC-701",
            owner_user_id=1,
            raw_name="Kelsei Martinez",
            raw_title="VP of Staffing",
            raw_company="Premier Staffing Solution LLC",
            raw_location="Chicago, Illinois, United States",
            raw_linkedin=profile_url,
            education="East Carolina University",
            followers_count="11,476 followers",
            connections_count="500+ connections",
            capture_id="VC-701",
            source_url=profile_url,
            source_page_title="Kelsei Martinez | LinkedIn",
            processing_status="pending",
        )

        # Observation 2: Scroll into About Section (VC-702)
        stg2 = DiscoveryStaging(
            batch_id="BATCH-KELSEI-PROG",
            discovery_id="DISC-KELSEI-02",
            device_id="VC-702",
            owner_user_id=1,
            raw_name="Kelsei Martinez",
            raw_linkedin=profile_url,
            about_summary="VP of Staffing at Premier Staffing Solution LLC with expertise in client relations and strategy",
            capture_id="VC-702",
            source_url=profile_url,
            source_page_title="Kelsei Martinez | LinkedIn",
            processing_status="pending",
        )

        # Observation 3: Scroll into Experience Section - Previous Employer (VC-703)
        stg3 = DiscoveryStaging(
            batch_id="BATCH-KELSEI-PROG",
            discovery_id="DISC-KELSEI-03",
            device_id="VC-703",
            owner_user_id=1,
            raw_name="Kelsei Martinez",
            raw_linkedin=profile_url,
            raw_title="Director of Recruiting",
            raw_company="ABC Staffing",
            previous_company="ABC Staffing",
            capture_id="VC-703",
            source_url=profile_url,
            source_page_title="Kelsei Martinez | LinkedIn",
            processing_status="pending",
        )

        # Observation 4: Scroll into Education Section (VC-704)
        stg4 = DiscoveryStaging(
            batch_id="BATCH-KELSEI-PROG",
            discovery_id="DISC-KELSEI-04",
            device_id="VC-704",
            owner_user_id=1,
            raw_name="Kelsei Martinez",
            raw_linkedin=profile_url,
            education="East Carolina University",
            capture_id="VC-704",
            source_url=profile_url,
            source_page_title="Kelsei Martinez | LinkedIn",
            processing_status="pending",
        )

        self.db.add_all([stg1, stg2, stg3, stg4])
        self.db.commit()

        # Run Batch Processor
        processor = DiscoveryProcessor(self.db)
        stats = processor.process_pending_batch()

        print("\n[TEST RESULT] Kelsei Profile Progressive Stats:", stats)

        # 1. Pipeline Verification: Exactly 1 NEW Person Created from 4 Observations
        self.assertEqual(stats["processed"], 4)
        self.assertEqual(stats["new"], 1, "Must resolve to exactly 1 person, NOT 4!")
        self.assertEqual(stats["rejected"], 0)

        # 2. ResolvedPerson State Verification
        resolved = self.db.query(ResolvedPerson).first()
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.canonical_name, "Kelsei Martinez")
        self.assertEqual(resolved.current_company, "Premier Staffing Solution LLC", "Current company must NEVER be overwritten by previous company")
        self.assertEqual(resolved.previous_company, "ABC Staffing", "Previous company must be captured in history")
        self.assertEqual(resolved.location, "Chicago, Illinois, United States")
        self.assertEqual(resolved.education, "East Carolina University")
        self.assertEqual(resolved.followers_count, "11,476 followers")
        self.assertEqual(resolved.connections_count, "500+ connections")
        self.assertIn("client relations", resolved.about_summary)
        self.assertEqual(resolved.observation_count, 4, "Must accumulate all 4 scroll observations")
        self.assertGreaterEqual(resolved.identity_confidence, 0.85)

        # 3. Master Database State Verification
        master_rec = self.db.query(Recruiter).first()
        self.assertIsNotNone(master_rec)
        self.assertEqual(master_rec.recruiter_name, "Kelsei Martinez")
        self.assertEqual(master_rec.location, "Chicago, Illinois, United States")
        self.assertEqual(master_rec.linkedin, profile_url)

        master_count = self.db.query(Recruiter).count()
        self.assertEqual(master_count, 1, "Master Recruiter table must have exactly 1 record")

        print("\n>>> KELSEI MARTINEZ PROGRESSIVE PROFILE REGRESSION: ALL ASSERTIONS PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
