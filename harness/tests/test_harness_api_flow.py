"""
harness/tests/test_harness_api_flow.py — End-to-End Multi-App Workflow & REST API Verification
"""
import sys
import os
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.hub import harness_hub
from backend.app.routes.harness import router


class TestHarnessApiFlow(unittest.TestCase):

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_01_api_status_endpoint(self):
        """Verifies GET /status returns valid matrix for all platforms."""
        resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("summary", data)
        self.assertIn("apps", data)
        self.assertIn("upcoming", data)
        
        apps = data["apps"]
        self.assertTrue(apps["teams"]["is_running"])
        self.assertTrue(apps["outlook"]["is_running"])
        self.assertTrue(apps["vitel"]["is_running"])
        self.assertTrue(apps["site"]["is_running"])
        print(f"\n  [PASS] API /status: 4/4 Core Platforms Active (Teams, Outlook, Vitel, Site).")

    def test_02_api_dispatch_candidate_flow(self):
        """Verifies POST /dispatch coordinates Teams, Outlook, and Vitel in one unified call."""
        candidate_payload = {
            "canonical_name": "Marcus Aurelius",
            "title": "Principal System Engineer",
            "company_name": "Apollo Global",
            "email": "marcus.aurelius@apolloglobal.com",
            "phone": "+1-415-555-9081",
            "targets": ["teams", "outlook", "vitel"]
        }

        # Mock Outlook create_email to avoid sending actual email in test
        with patch.object(harness_hub.get_connector("outlook"), "create_email", return_value=True):
            resp = self.client.post("/dispatch", json=candidate_payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            self.assertTrue(data["success"])
            self.assertEqual(data["candidate"], "Marcus Aurelius")
            actions = data["actions"]

            # Teams verified
            self.assertIn("teams", actions)
            self.assertTrue(actions["teams"]["success"])

            # Outlook verified
            self.assertIn("outlook", actions)
            self.assertTrue(actions["outlook"]["success"])
            self.assertEqual(actions["outlook"]["recipient"], "marcus.aurelius@apolloglobal.com")

            # Vitel verified
            self.assertIn("vitel", actions)
            self.assertTrue(actions["vitel"]["success"])
            self.assertEqual(actions["vitel"]["recipient"], "+14155559081")

        print("  [PASS] API /dispatch: Multi-Platform Flow coordinated across Teams, Outlook, and Vitel.")

    def test_03_mini_ui_endpoint(self):
        """Verifies GET /ui serves the compact visual harness interface."""
        resp = self.client.get("/ui")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("TalentOps Unified Platform Controller", resp.text)
        self.assertIn("Interactive Command & Task Console", resp.text)
        print("  [PASS] API /ui: Mini Dashboard Interface served successfully (HTTP 200).")


if __name__ == "__main__":
    unittest.main()
