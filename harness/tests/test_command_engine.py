"""
harness/tests/test_command_engine.py — Command Engine Parsing & Normalization Verification
"""
import sys
import os
import unittest

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.command_engine import CommandEngine


class TestCommandEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CommandEngine()

    def test_01_natural_language_normalization(self):
        """Verifies natural language requests translate to standard internal handlers."""
        tests = [
            ("status", "status"),
            ("system status", "status"),
            ("check outlook inbox", "check_inbox"),
            ("read email 10", "check_inbox"),
            ("check call log", "check_calls"),
            ("recent candidates", "staged_candidates"),
            ("focus vitel", "focus"),
            ("help", "help"),
        ]
        for query, expected_cmd in tests:
            norm_cmd, _ = self.engine._normalize_command(query)
            self.assertEqual(norm_cmd, expected_cmd, f"Query '{query}' should normalize to '{expected_cmd}'")
        print("\n  [PASS] Natural Language Request Normalization verified.")

    def test_02_structured_command_parsing(self):
        """Verifies structured CLI tokenization and parameter extraction."""
        cmd, params = self.engine._normalize_command('outreach "Sarah Connor" sarah@cyber.com +14155550199 "Cyberdyne"')
        self.assertEqual(cmd, "outreach")
        self.assertEqual(params["name"], "Sarah Connor")
        self.assertEqual(params["email"], "sarah@cyber.com")
        self.assertEqual(params["phone"], "+14155550199")
        self.assertEqual(params["company"], "Cyberdyne")

        cmd, params = self.engine._normalize_command('sms 2065551234 "Hello from TalentOps"')
        self.assertEqual(cmd, "sms")
        self.assertEqual(params["phone"], "2065551234")
        self.assertEqual(params["message"], "Hello from TalentOps")
        print("  [PASS] Structured Command Parsing & Parameter Extraction verified.")

    def test_03_help_and_unknown_commands(self):
        """Verifies help topic generation and friendly unknown command handling."""
        res = self.engine.execute("help")
        self.assertTrue(res["success"])
        self.assertIn("commands", res["result"])

        bad_res = self.engine.execute("fly_to_moon")
        self.assertFalse(bad_res["success"])
        self.assertIn("Unknown command", bad_res["error"])
        print("  [PASS] Help and Unknown Command Fallbacks verified.")


if __name__ == "__main__":
    unittest.main()
