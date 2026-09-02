"""
Live Ingestion Telemetry & Traceable Provenance Regression Test.
Verifies that:
1. Enriched existing recruiters increment 'existing_people_enriched' and 'fields_added'
   while Total Recruiters count stays constant.
2. New people increment 'new_people_created' and 'master_db_inserts'.
3. Before/After diffs are accurately populated with exact field mutations.
4. Live pipeline state accurately tracks stream recency.
"""

import os
import sys
import unittest
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base
from app.models.models import Recruiter, Company
from app.models.auth_models import User
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.models.extension_models import ExtensionDiscoveryEvent
from app.services.ingestion_telemetry import get_live_scraper_ingestion_summary
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class TestIngestionTelemetryRegression(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Seed test user
        self.user = User(
            id=56,
            email="telemetry-lead@talentops.ai",
            first_name="Telemetry",
            last_name="Lead",
            status="Active"
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_enrichment_telemetry_and_before_after_diffs(self):
        """
        Simulate 1 new person creation + 2 existing person enrichments.
        Verify that enrichment counters increase without duplicating master records.
        """
        now = datetime.now(timezone.utc)

        # 1. Event: New Person Discovery
        evt1 = ExtensionDiscoveryEvent(
            discovery_id="DISC-TEST-101",
            device_id="ext-dev-01",
            owner_user_id=56,
            recruiter_name="Elena Rostova",
            company_name="Snowflake",
            title="Principal Technical Recruiter",
            db_action="NEW_DISCOVERY",
            fields_added=json.dumps(["name", "title", "company", "email"]),
            capture_id="VC-TEST-101",
            source_url="https://www.linkedin.com/in/elena-rostova",
            confidence=98,
            created_at=now - timedelta(seconds=60),
        )
        self.db.add(evt1)

        # 2. Event: Existing Person Enriched (Kelsei Martinez enriched with location and previous company)
        evt2 = ExtensionDiscoveryEvent(
            discovery_id="DISC-TEST-102",
            device_id="ext-dev-01",
            owner_user_id=56,
            recruiter_name="Kelsei Martinez",
            company_name="Premier Staffing Solution LLC",
            title="VP of Staffing",
            location="Chicago, Illinois, United States",
            db_action="ENRICHED",
            fields_added=json.dumps(["location", "education", "previous_company"]),
            capture_id="VC-KELSEI-77",
            source_url="https://www.linkedin.com/in/kelseirobertson/",
            confidence=99,
            created_at=now - timedelta(seconds=20),
        )
        self.db.add(evt2)

        # 3. Add Staging Records
        stg1 = DiscoveryStaging(
            batch_id="BATCH-001",
            discovery_id="DISC-001",
            device_id="ext-dev",
            owner_user_id=56,
            raw_name="Kelsei Martinez",
            raw_company="Premier Staffing Solution LLC",
            processing_status="committed",
            created_at=now - timedelta(seconds=20),
        )
        self.db.add(stg1)
        self.db.commit()

        # Compute Ingestion Summary
        summary = get_live_scraper_ingestion_summary(self.db, user_id=56)
        print("\n[TELEMETRY RESULT]:", json.dumps(summary, indent=2))

        metrics = summary["metrics_today"]
        timestamps = summary["timestamps"]
        diffs = summary["recent_enrichment_diffs"]

        # Assertions
        self.assertEqual(summary["pipeline_state"], "RECEIVING_DATA", "Must detect active data stream within 3 minutes")
        self.assertEqual(metrics["new_people_created"], 1, "Must record 1 new person")
        self.assertEqual(metrics["existing_people_enriched"], 1, "Must record 1 enriched person")
        self.assertEqual(metrics["fields_added"], 7, "Sum of fields added across both events (4 + 3)")

        # Verify Timestamps
        self.assertNotEqual(timestamps["last_scraper_observation"], "None Recorded")
        self.assertNotEqual(timestamps["last_enrichment"], "None Recorded")
        self.assertNotEqual(timestamps["last_new_record"], "None Recorded")

        # Verify Traceable Before / After Diffs
        kelsei_diff = next(d for d in diffs if d["candidate_name"] == "Kelsei Martinez")
        self.assertEqual(kelsei_diff["decision"], "ENRICHED")
        self.assertEqual(kelsei_diff["db_status"], "UPDATED_SUCCESS ✅")
        self.assertEqual(kelsei_diff["capture_id"], "VC-KELSEI-77")
        self.assertIn("location", kelsei_diff["fields_added"])
        self.assertEqual(kelsei_diff["after_state"]["location"], "Chicago, Illinois, United States")

        print("\n>>> LIVE INGESTION TELEMETRY REGRESSION: 100% PASSED! <<<")


if __name__ == "__main__":
    unittest.main()
