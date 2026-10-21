"""
harness/tests/test_multi_app_harness.py — Multi-App Harness Connector Verification
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.connectors.base_connector import BaseConnector
from harness.connectors.teams_connector import teams_connector, TeamsConnector
from harness.connectors.outlook_connector import outlook_connector, OutlookConnector
from harness.connectors.vitel_connector import vitel_connector, VitelConnector
from harness.connectors.site_connector import site_connector, SiteConnector


class TestMultiAppHarness(unittest.TestCase):

    def test_01_teams_connector_interface(self):
        """Verifies Teams connector status, interface compliance, and capabilities."""
        self.assertIsInstance(teams_connector, BaseConnector)
        self.assertEqual(teams_connector.app_name, "teams")
        status = teams_connector.get_status()
        self.assertIn("is_running", status)
        self.assertIn("capabilities", status)
        self.assertIn("open_chat", status["capabilities"])
        print(f"\n  [PASS] Teams Connector: running={status['is_running']}, type={status.get('version_type')}")

    def test_02_outlook_connector_interface(self):
        """Verifies Outlook connector status, COM/MAPI session, and capabilities."""
        self.assertIsInstance(outlook_connector, BaseConnector)
        self.assertEqual(outlook_connector.app_name, "outlook")
        status = outlook_connector.get_status()
        self.assertIn("is_running", status)
        self.assertIn("inbox_count", status)
        self.assertIn("capabilities", status)
        self.assertIn("create_email", status["capabilities"])
        print(f"  [PASS] Outlook Connector: running={status['is_running']}, inbox_items={status['inbox_count']}")

    def test_03_vitel_connector_interface(self):
        """Verifies Vitel connector status, local database telemetry, and SMS staging."""
        self.assertIsInstance(vitel_connector, BaseConnector)
        self.assertEqual(vitel_connector.app_name, "vitel")
        status = vitel_connector.get_status()
        self.assertIn("is_running", status)
        self.assertIn("active_account", status)
        self.assertIn("capabilities", status)
        self.assertIn("prepare_sms", status["capabilities"])
        
        # Test SMS staging logic
        sms_res = vitel_connector.prepare_sms("2065550199", "Hello from TalentOps")
        self.assertTrue(sms_res["success"])
        self.assertEqual(sms_res["recipient"], "+12065550199")
        print(f"  [PASS] Vitel Connector: running={status['is_running']}, account='{status['active_account']}', SMS formatted.")

    def test_04_site_connector_interface(self):
        """Verifies TalentOps Web Site connector status and pipeline access."""
        self.assertIsInstance(site_connector, BaseConnector)
        self.assertEqual(site_connector.app_name, "site")
        status = site_connector.get_status()
        self.assertIn("is_running", status)
        self.assertIn("staged_observations_count", status)
        self.assertGreater(status["staged_observations_count"], 0)
        print(f"  [PASS] TalentOps Site Connector: running={status['is_running']}, staged_queue={status['staged_observations_count']}")


if __name__ == "__main__":
    unittest.main()
