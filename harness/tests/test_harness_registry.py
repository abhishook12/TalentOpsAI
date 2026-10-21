"""
harness/tests/test_harness_registry.py — Dynamic Registry & Extensible Upcoming Apps Verification
"""
import sys
import os
import unittest
from typing import Dict, Any, Optional

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.hub import HarnessHub
from harness.connectors.base_connector import BaseConnector


class MockCustomCrmConnector(BaseConnector):
    """Simulates an upcoming custom CRM platform connector."""
    def __init__(self):
        super().__init__(app_name="custom_crm", display_name="Enterprise CRM")
        self.action_history = []

    def is_running(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "display_name": self.display_name,
            "is_running": True,
            "synced_leads": 1250,
            "capabilities": ["sync_candidate", "tag_lead", "bring_to_front"],
        }

    def bring_to_front(self) -> bool:
        return True

    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.action_history.append((action, payload))
        return {"action": action, "success": True, "lead_id": "CRM-9921"}


class TestHarnessRegistry(unittest.TestCase):

    def setUp(self):
        self.hub = HarnessHub()

    def test_01_core_connectors_present(self):
        """Verifies that all 4 core platforms are registered in the hub."""
        connectors = self.hub.list_connectors()
        self.assertIn("teams", connectors)
        self.assertIn("outlook", connectors)
        self.assertIn("vitel", connectors)
        self.assertIn("site", connectors)
        print(f"\n  [PASS] Core Connectors Registered: {connectors}")

    def test_02_upcoming_apps_tracking(self):
        """Verifies that upcoming apps (WhatsApp, RingCentral, Slack) are tracked."""
        matrix = self.hub.get_status_matrix()
        upcoming = matrix["upcoming"]
        self.assertIn("whatsapp", upcoming)
        self.assertIn("ringcentral", upcoming)
        self.assertIn("slack", upcoming)
        print(f"  [PASS] Upcoming Roadmap Apps: {list(upcoming.keys())}")

    def test_03_dynamic_runtime_plugin_registration(self):
        """Verifies dynamic plug-in of a new application connector at runtime without code changes."""
        mock_crm = MockCustomCrmConnector()
        self.hub.register_connector("custom_crm", mock_crm)

        # Confirm connector exists
        conn = self.hub.get_connector("custom_crm")
        self.assertIsNotNone(conn)
        self.assertEqual(conn.display_name, "Enterprise CRM")

        # Confirm status matrix includes it
        matrix = self.hub.get_status_matrix()
        self.assertIn("custom_crm", matrix["apps"])
        self.assertEqual(matrix["apps"]["custom_crm"]["synced_leads"], 1250)

        # Confirm action dispatch works
        res = conn.execute_action("sync_candidate", {"name": "Test Candidate"})
        self.assertTrue(res["success"])
        self.assertEqual(res["lead_id"], "CRM-9921")
        print("  [PASS] Dynamic Plugin Extensibility: New connector registered and executed successfully.")


if __name__ == "__main__":
    unittest.main()
