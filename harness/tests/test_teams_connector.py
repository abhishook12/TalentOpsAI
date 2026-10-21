"""
harness/tests/test_teams_connector.py — Automated Verification for Teams Connector
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.connectors.teams_connector import TeamsConnector


class TestTeamsConnector(unittest.TestCase):

    def setUp(self):
        self.connector = TeamsConnector()

    def test_01_process_status(self):
        """Verify process detection correctly identifies ms-teams.exe on this PC."""
        status = self.connector.get_process_status()
        self.assertIsInstance(status, dict)
        self.assertIn("is_running", status)
        self.assertIn("pids", status)
        self.assertIn("is_new_teams", status)
        self.assertIn("version_type", status)
        # We know ms-teams is running on this machine (PIDs 10732, 12400)
        self.assertTrue(status["is_running"], "Teams process must be detected as running")
        self.assertTrue(status["is_new_teams"], "Must identify New Teams (MSIX WebView2)")
        print(f"\n  [PASS] Process Status: {status['version_type']} (PIDs: {status['pids']})")

    def test_02_deep_link_uri_generation(self):
        """Verify URI parameter encoding and deep-link generation."""
        with patch.object(self.connector, "_launch_uri", return_value=True) as mock_launch:
            # 1. Chat without message
            res = self.connector.open_chat("alice@company.com")
            self.assertTrue(res)
            mock_launch.assert_called_with("msteams:/l/chat/0/0?users=alice%40company.com")

            # 2. Chat with message
            res = self.connector.open_chat("bob@company.com", "Review candidate Kitab Ali")
            self.assertTrue(res)
            mock_launch.assert_called_with("msteams:/l/chat/0/0?users=bob%40company.com&message=Review+candidate+Kitab+Ali")

            # 3. Audio Call
            res = self.connector.start_call("charlie@company.com", with_video=False)
            self.assertTrue(res)
            mock_launch.assert_called_with("msteams:/l/call/0/0?users=charlie%40company.com&withVideo=false")

            # 4. Video Call
            res = self.connector.start_call("charlie@company.com", with_video=True)
            self.assertTrue(res)
            mock_launch.assert_called_with("msteams:/l/call/0/0?users=charlie%40company.com&withVideo=true")

            # 5. Empty inputs
            self.assertFalse(self.connector.open_chat(""))
            self.assertFalse(self.connector.start_call(""))
        print("  [PASS] Deep-Link URI Generation & Parameter Encoding verified.")

    def test_03_candidate_card_payload_structure(self):
        """Verify Adaptive / MessageCard JSON payload schema matches Microsoft specs."""
        candidate = {
            "canonical_name": "Kitab Ali",
            "title": "Senior Technical Recruiter",
            "company_name": "Amazon",
            "location": "Seattle, WA",
            "email": "kitab.ali@amazon.com",
            "phone": "+1 206-555-0199",
            "linkedin_url": "https://www.linkedin.com/in/kitab-ali",
        }

        captured_payload = None

        def mock_post(url, data):
            nonlocal captured_payload
            captured_payload = data
            return True

        with patch.object(self.connector, "_post_json", side_effect=mock_post):
            success = self.connector.send_candidate_card(
                candidate_data=candidate,
                webhook_url="https://mock.webhook.office.com/webhookb2/..."
            )
            self.assertTrue(success)
            self.assertIsNotNone(captured_payload)
            self.assertEqual(captured_payload["@type"], "MessageCard")
            self.assertEqual(captured_payload["title"], "🎯 TalentOps Sourced: Kitab Ali")
            
            # Verify facts
            facts = captured_payload["sections"][0]["facts"]
            fact_dict = {f["name"]: f["value"] for f in facts}
            self.assertEqual(fact_dict["Current Role:"], "Senior Technical Recruiter")
            self.assertEqual(fact_dict["Organization:"], "Amazon")
            self.assertEqual(fact_dict["Email:"], "kitab.ali@amazon.com")

            # Verify action button
            actions = captured_payload["potentialAction"]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["name"], "🔗 View Profile")
            self.assertEqual(actions[0]["targets"][0]["uri"], "https://www.linkedin.com/in/kitab-ali")
        print("  [PASS] Candidate Dossier Card payload formatting verified.")

    def test_04_window_enumeration_safe(self):
        """Verify window detection runs safely without exceptions."""
        windows = self.connector.find_teams_windows()
        self.assertIsInstance(windows, list)
        print(f"  [PASS] Window Enumeration executed successfully (Found {len(windows)} active window(s)).")


if __name__ == "__main__":
    unittest.main()
