"""
Automated Regression Test Suite for SynergyGrid IT Screen & Multi-Person Context Resolution.

Verifies:
1. Multi-person enumeration (Mihir Roy, Kenny Shaw, Apurva C.).
2. Separation of source_platform ('LinkedIn') and employer company ('SynergyGrid IT').
3. Context inheritance (page context -> cards without explicit company).
4. Strict rejection of UI action buttons ('Connect', 'Message', 'Contact', 'Follow') from titles.
5. Batch processor execution into master directory with accurate provenance.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.extension_models import ExtensionDevice, ExtensionDiscoveryEvent
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.services.discovery_processor import DiscoveryProcessor, run_batch_processor

class TestSynergyGridRegression(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user & device
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

    def test_synergygrid_multi_person_context_resolution(self):
        """
        Simulate the exact SynergyGrid IT People page screenshot:
        - Mihir Roy: 'Recruiting Manager at SynergyGrid IT' (with UI action 'Connect')
        - Kenny Shaw: 'Vice President at SynergyGrid IT' (with UI action 'Connect')
        - Apurva C.: 'Senior Recruiter' (with UI action 'Message', company inherited from page context)
        """
        batch_id = "BATCH-SYNERGY-001"
        page_url = "https://www.linkedin.com/company/synergygrid-it/people/"
        page_title = "SynergyGrid IT: People | LinkedIn"

        # 1. Stage the 3 raw observations
        obs1 = DiscoveryStaging(
            batch_id=batch_id,
            discovery_id="DISC-MIHIR-001",
            device_id="DEV-SCOUT-01",
            owner_user_id=1,
            raw_name="Mihir Roy · 2nd",
            raw_title="Recruiting Manager at SynergyGrid IT",
            raw_company="SynergyGrid IT",
            raw_linkedin="https://www.linkedin.com/in/mihir-roy-12345/",
            source_url=page_url,
            source_page_title=page_title,
            processing_status="pending"
        )

        obs2 = DiscoveryStaging(
            batch_id=batch_id,
            discovery_id="DISC-KENNY-001",
            device_id="DEV-SCOUT-01",
            owner_user_id=1,
            raw_name="Kenny Shaw · 2nd",
            raw_title="Vice President at SynergyGrid IT",
            raw_company="SynergyGrid IT",
            raw_linkedin="https://www.linkedin.com/in/kenny-shaw-67890/",
            source_url=page_url,
            source_page_title=page_title,
            processing_status="pending"
        )

        # Apurva has no explicit company in raw headline, title is 'Senior Recruiter', button was 'Message'
        obs3 = DiscoveryStaging(
            batch_id=batch_id,
            discovery_id="DISC-APURVA-001",
            device_id="DEV-SCOUT-01",
            owner_user_id=1,
            raw_name="Apurva C. · 3rd",
            raw_title="Senior Recruiter",
            raw_company="",  # Missing in card, must inherit from page context
            raw_linkedin="https://www.linkedin.com/in/apurva-c-54321/",
            source_url=page_url,
            source_page_title=page_title,
            processing_status="pending"
        )

        self.db.add_all([obs1, obs2, obs3])
        self.db.commit()

        # 2. Run Batch Intelligence Processor
        processor = DiscoveryProcessor(self.db)
        stats = processor.process_pending_batch()

        print(f"\n[Batch Processor Stats] {stats}")
        self.assertEqual(stats["processed"], 3, "Must process all 3 staging records")
        self.assertEqual(stats["new"], 3, "Must create 3 new master candidate profiles")

        # 3. Verify ResolvedPerson entities
        resolved = self.db.query(ResolvedPerson).all()
        self.assertEqual(len(resolved), 3, "Must create exactly 3 resolved persons")

        r_mihir = self.db.query(ResolvedPerson).filter(ResolvedPerson.canonical_name == "Mihir Roy").first()
        self.assertIsNotNone(r_mihir, "Mihir Roy resolved person must exist")
        self.assertEqual(r_mihir.current_title, "Recruiting Manager")
        self.assertEqual(r_mihir.current_company, "SynergyGrid IT")
        self.assertNotEqual(r_mihir.current_company, "LinkedIn", "Company must NEVER be 'LinkedIn'")
        self.assertNotEqual(r_mihir.current_title, "Contact", "Title must NEVER be 'Contact'")

        r_kenny = self.db.query(ResolvedPerson).filter(ResolvedPerson.canonical_name == "Kenny Shaw").first()
        self.assertIsNotNone(r_kenny, "Kenny Shaw resolved person must exist")
        self.assertEqual(r_kenny.current_title, "Vice President")
        self.assertEqual(r_kenny.current_company, "SynergyGrid IT")

        r_apurva = self.db.query(ResolvedPerson).filter(ResolvedPerson.canonical_name == "Apurva C.").first()
        self.assertIsNotNone(r_apurva, "Apurva C. resolved person must exist")
        self.assertEqual(r_apurva.current_title, "Senior Recruiter")
        self.assertEqual(r_apurva.current_company, "SynergyGrid IT", "Apurva must inherit SynergyGrid IT from page title context")
        self.assertNotEqual(r_apurva.current_title, "Message", "Title must NEVER be UI action 'Message'")

        # 4. Verify Master Database Records
        recruiters = self.db.query(Recruiter).all()
        self.assertEqual(len(recruiters), 3, "Master recruiters table must contain exactly 3 profiles")

        # Company record check
        company = self.db.query(Company).filter(Company.company_name == "SynergyGrid IT").first()
        self.assertIsNotNone(company, "Company 'SynergyGrid IT' must exist in master table")
        self.assertIsNone(self.db.query(Company).filter(Company.company_name == "LinkedIn").first(), "'LinkedIn' must NEVER be created as employer company")

        for rec in recruiters:
            self.assertEqual(rec.company_id, company.company_id, f"{rec.recruiter_name} must be associated with SynergyGrid IT")
            self.assertNotIn(rec.title.lower(), ["connect", "message", "contact", "follow"], f"{rec.recruiter_name} title must not be a UI action")

        print("\n>>> SYNERGYGRID REGRESSION SUITE: ALL ASSERTIONS PASSED! <<<")

if __name__ == "__main__":
    unittest.main()
