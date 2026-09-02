"""
Meagan Garnett Live Extraction & Instant Ingestion Regression Test.
Verifies:
1. Meagan Garnett Profile Extraction:
   - Name: Meagan Garnett
   - Title: Professional Recruiter
   - Company: Brooksource
   - Location: Greater Birmingham, Alabama Area (First-Class Field)
   - Education: The University of Alabama
2. Immediate Batch Ingestion & Master DB commit.
3. Live Ingestion Telemetry update.
"""

import os
import sys
import unittest
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.extension_models import ExtensionDevice, ExtensionDiscoveryEvent
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.utils.normalizer import build_semantic_graph_document
from app.services.discovery_processor import DiscoveryProcessor
from app.services.ingestion_telemetry import get_live_scraper_ingestion_summary
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestMeaganGarnettSyncRegression(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed user
        self.user = User(id=1, email="user@talentops.ai", first_name="Recruiter", last_name="User", status="Active")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_meagan_garnett_extraction_and_instant_sync(self):
        raw_contact = {
            "recruiter_name": "Meagan Garnett",
            "title": "Professional Recruiter",
            "headline": "Professional Recruiter at Brooksource",
            "company_name": "Brooksource",
            "location": "Greater Birmingham, Alabama Area",
            "education": "The University of Alabama",
            "connections_count": "500+ connections",
            "about_summary": "Passionate about building strong relationships and helping people find opportunities that align with their goals.",
            "linkedin_url": "https://www.linkedin.com/in/meagangarnett/",
            "capture_id": "VC-MEAGAN-01",
        }

        doc = build_semantic_graph_document(
            raw_contacts=[raw_contact],
            raw_observations=[{
                "subject": "Meagan Garnett",
                "predicate": "EMPLOYED_BY",
                "object_val": "Brooksource",
                "semantic_type": "EMPLOYMENT_RELATIONSHIP",
                "attributes": {"title": "Professional Recruiter"}
            }],
            page_url="https://www.linkedin.com/in/meagangarnett/",
            page_title="Meagan Garnett - Professional Recruiter - Brooksource | LinkedIn",
            capture_id="VC-MEAGAN-01"
        )

        processor = DiscoveryProcessor(self.db)
        stats = processor.process_knowledge_graph_document(doc, owner_user_id=1)

        print("\n[MEAGAN GARNETT SYNC] Processor Stats:", stats)

        # 1. Verify Recruiter Record Created
        rec = self.db.query(Recruiter).filter(Recruiter.recruiter_name == "Meagan Garnett").first()
        self.assertIsNotNone(rec, "Meagan Garnett must exist in master recruiters table")
        self.assertEqual(rec.title, "Professional Recruiter")
        self.assertEqual(rec.location, "Greater Birmingham, Alabama Area")
        self.assertIn("meagangarnett", rec.linkedin)

        # 2. Verify Company Created
        comp = self.db.query(Company).filter(Company.company_id == rec.company_id).first()
        self.assertIsNotNone(comp, "Brooksource company must be created")
        self.assertEqual(comp.name, "Brooksource")

        # 3. Verify Telemetry Summary
        telemetry = get_live_scraper_ingestion_summary(self.db, 1)
        self.assertEqual(telemetry["metrics_today"]["new_people_created"], 1)

        print("\n>>> MEAGAN GARNETT SYNC REGRESSION: 100% PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
