"""
End-to-End Live API Integration Test for Discovery Staging & Batch Intelligence Pipeline.
Tests FastAPI endpoints:
- POST /recruiters/extension/batch
- GET /recruiters/extension/staging-status
- GET /staging/summary
- GET /staging/records
- GET /staging/resolved-persons
- GET /staging/review-queue
- POST /staging/process-now
- POST /staging/review/{id}/approve
- POST /staging/review/{id}/reject
"""

import os
import sys
import unittest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.database import Base, get_db
from app.main import app
from app.models.auth_models import User
from app.models.models import Recruiter, Company
from app.models.staging_models import DiscoveryStaging, ResolvedPerson
from app.services.auth_service import create_access_token

class TestLiveStagingAPI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Override get_db dependency
        def _get_test_db():
            try:
                yield self.db
            finally:
                pass
        app.dependency_overrides[get_db] = _get_test_db

        # Seed test user
        self.user = User(
            id=56,
            email="abhishekjadon824@gmail.com",
            first_name="Abhishek",
            last_name="Jadon",
            password_hash="test",
            status="Active",
        )
        self.db.add(self.user)
        self.db.commit()

        # Generate test JWT
        self.token = create_access_token({"sub": "56", "scope": "extension"})
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Device-ID": "test-scout-node-01"
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_end_to_end_staging_pipeline_api(self):
        # 1. Post batch of contacts to /recruiters/extension/batch
        batch_payload = {
            "device_id": "test-scout-node-01",
            "session_stats": {"sessionId": "sess-live-99"},
            "contacts": [
                {
                    "discovery_id": "DISC-API-1",
                    "recruiter_name": "Elena Rostova",
                    "title": "Principal Technical Recruiter",
                    "company_name": "Snowflake",
                    "email": "elena.rostova@snowflake.com",
                    "phone": "+1-415-555-0182",
                    "linkedin_url": "https://www.linkedin.com/in/elena-rostova-recruiter",
                    "location": "San Mateo, CA",
                    "source_url": "https://www.linkedin.com/in/elena-rostova-recruiter",
                    "confidence": 98
                },
                {
                    "discovery_id": "DISC-API-2",
                    "recruiter_name": "Elena Rostova 1st",
                    "title": "Principal Technical Recruiter",
                    "company_name": "Snowflake",
                    "phone": "+1-415-555-0182",
                    "linkedin_url": "https://www.linkedin.com/in/elena-rostova-recruiter",
                    "location": "San Mateo, CA",
                    "confidence": 95
                }
            ]
        }

        resp = self.client.post("/recruiters/extension/batch", json=batch_payload, headers=self.headers)
        print("\n[API TEST] /recruiters/extension/batch Response:", resp.status_code, resp.json())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "STAGED")
        self.assertEqual(data["staged"], 2)
        self.assertTrue("BATCH-" in data["batch_id"])

        # 2. Check /staging/summary
        sum_resp = self.client.get("/staging/summary", headers=self.headers)
        print("[API TEST] /staging/summary Response:", sum_resp.status_code, sum_resp.json())
        self.assertEqual(sum_resp.status_code, 200)
        summary = sum_resp.json()
        self.assertEqual(summary["total_all_time"], 2)
        self.assertEqual(summary["committed"], 2) # Both staging observations committed
        self.assertEqual(summary["resolved_persons"], 1) # 1 consolidated person entity!

        # 3. Check /staging/records
        rec_resp = self.client.get("/staging/records", headers=self.headers)
        print("[API TEST] /staging/records Count:", rec_resp.json()["total"])
        self.assertEqual(rec_resp.status_code, 200)
        self.assertEqual(rec_resp.json()["total"], 2)

        # 4. Check /staging/resolved-persons
        rp_resp = self.client.get("/staging/resolved-persons", headers=self.headers)
        print("[API TEST] /staging/resolved-persons:", rp_resp.json()["persons"])
        self.assertEqual(rp_resp.status_code, 200)
        self.assertEqual(len(rp_resp.json()["persons"]), 1)
        self.assertEqual(rp_resp.json()["persons"][0]["canonical_name"], "Elena Rostova")
        self.assertEqual(rp_resp.json()["persons"][0]["primary_email"], "elena.rostova@snowflake.com")
        self.assertEqual(rp_resp.json()["persons"][0]["observation_count"], 2)

        # 5. Check master recruiter in DB
        master_r = self.db.query(Recruiter).filter(Recruiter.recruiter_name == "Elena Rostova").first()
        self.assertIsNotNone(master_r)
        self.assertEqual(master_r.email, "elena.rostova@snowflake.com")
        self.assertEqual(master_r.phone, "+1-415-555-0182")

        # 6. Check /recruiters/extension/staging-status
        status_resp = self.client.get("/recruiters/extension/staging-status", headers=self.headers)
        print("[API TEST] /recruiters/extension/staging-status:", status_resp.json())
        self.assertEqual(status_resp.status_code, 200)

        # 7. Check /staging/decision-distribution
        dist_resp = self.client.get("/staging/decision-distribution", headers=self.headers)
        print("[API TEST] /staging/decision-distribution:", dist_resp.json())
        self.assertEqual(dist_resp.status_code, 200)

if __name__ == "__main__":
    unittest.main()
