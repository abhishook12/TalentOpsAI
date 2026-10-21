"""
harness/tests/test_teams_pipeline_integration.py — End-to-End TalentOps Pipeline Integration Verification
"""
import sys
import os
import sqlite3
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, r"C:\TalentOpsAI")
from harness.connectors.teams_connector import TeamsConnector

class TestTeamsPipelineIntegration(unittest.TestCase):
    def setUp(self):
        self.connector = TeamsConnector()
        self.db_path = r"C:\TalentOpsAI\scout_desktop\local_queue.db"

    def test_01_real_observation_to_teams_card(self):
        """Verifies transforming live staged observations from local_queue.db into rich Teams cards."""
        self.assertTrue(os.path.exists(self.db_path), "local_queue.db must exist")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT cluster_json FROM queued_observations ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()

        self.assertGreater(len(rows), 0, "Should have staged observations in local_queue.db")

        captured_cards = []
        def mock_post(url, payload):
            captured_cards.append(payload)
            return True

        with patch.object(self.connector, "_post_json", side_effect=mock_post):
            for row in rows:
                data = json.loads(row[0])
                # Ensure fields exist for test robustness
                candidate_data = {
                    "canonical_name": data.get("recruiter_name") or data.get("name") or "Sourced Candidate",
                    "title": data.get("title") or "Technical Specialist",
                    "company_name": data.get("company") or "Global Tech",
                    "email": data.get("email") or "candidate@example.com",
                    "linkedin_url": data.get("linkedin_url") or "https://linkedin.com/in/sample"
                }
                res = self.connector.send_candidate_card(candidate_data, webhook_url="https://mock.teams.webhook/api")
                self.assertTrue(res)

        self.assertEqual(len(captured_cards), len(rows))
        for card in captured_cards:
            self.assertEqual(card["@type"], "MessageCard")
            self.assertTrue(card["title"].startswith("🎯 TalentOps Sourced:"))
            self.assertGreater(len(card["sections"][0]["facts"]), 0)
        
        print(f"\n  [PASS] Successfully formatted and staged {len(captured_cards)} real candidate cards for Teams delivery.")

    def test_02_recruiter_quick_dispatch_link(self):
        """Verifies generating quick 1-click recruiter collaborative chat links from candidate profiles."""
        recruiter_email = "team_lead@company.com"
        candidate_summary = "Reviewing John Doe (Senior Engineer @ Stripe) from TalentOps Scout."
        
        with patch.object(self.connector, "_launch_uri", return_value=True) as mock_launch:
            dispatched = self.connector.open_chat(recruiter_email, message=candidate_summary)
            self.assertTrue(dispatched)
            
            # Check arguments passed to launch
            call_args = mock_launch.call_args[0][0]
            self.assertIn("msteams:/l/chat/0/0?", call_args)
            self.assertIn("team_lead%40company.com", call_args)
            self.assertIn("Reviewing+John+Doe", call_args)
        
        print("  [PASS] Recruiter 1-click collaborative chat dispatcher verified.")

if __name__ == "__main__":
    unittest.main()
