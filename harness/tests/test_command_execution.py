"""
harness/tests/test_command_execution.py — Live Cross-Platform Command Execution Verification
"""
import sys
import os
import unittest

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.command_engine import command_engine


class TestCommandExecution(unittest.TestCase):

    def test_01_execute_status(self):
        """Verifies executing 'status' command retrieves the live multi-platform matrix."""
        res = command_engine.execute("status")
        self.assertTrue(res["success"])
        self.assertEqual(res["command"], "status")
        summary = res["result"]["summary"]
        self.assertEqual(summary["total_connected_apps"], 4)
        self.assertEqual(summary["active_apps_count"], 4)
        print(f"\n  [PASS] 'status' command executed: {summary['active_apps_count']}/4 apps active.")

    def test_02_execute_staged_candidates(self):
        """Verifies executing 'staged_candidates' pulls live observations from local pipeline."""
        res = command_engine.execute("staged_candidates 3")
        self.assertTrue(res["success"])
        candidates = res["result"]["staged_candidates"]
        self.assertGreater(len(candidates), 0)
        print(f"  [PASS] 'staged_candidates' command executed: Retreived {len(candidates)} candidates.")

    def test_03_execute_vitel_calls(self):
        """Verifies executing 'check_calls' queries local Vitel event telemetry."""
        res = command_engine.execute("check_calls 3")
        self.assertTrue(res["success"])
        logs = res["result"]["call_logs"]
        self.assertIsInstance(logs, list)
        print(f"  [PASS] 'check_calls' command executed: Retrieved {len(logs)} log entries from Vitel database.")

    def test_04_execute_sms_staging(self):
        """Verifies executing 'sms' prepares and formats candidate SMS dispatch."""
        res = command_engine.execute('sms 4155551234 "Your interview is confirmed for tomorrow."')
        self.assertTrue(res["success"])
        vitel_res = res["result"]
        self.assertEqual(vitel_res["recipient"], "+14155551234")
        self.assertEqual(vitel_res["status"], "staged_for_dispatch")
        print("  [PASS] 'sms' command executed: Successfully staged candidate SMS.")

    def test_05_execute_register_app(self):
        """Verifies dynamically registering an upcoming app through the command interface."""
        res = command_engine.execute('register_app signal "Signal Desktop" Messaging "Encrypted recruiter chat"')
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["registered"], "signal")
        print("  [PASS] 'register_app' command executed: New upcoming app dynamically registered.")


if __name__ == "__main__":
    unittest.main()
