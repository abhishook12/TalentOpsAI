"""
harness/tests/test_sequence_engine.py — Sequence Engine & Natural Language Verification
=======================================================================================
"""

import unittest
from harness.sequence_engine import SequenceEngine
from harness.command_engine import command_engine


class TestSequenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SequenceEngine(":memory:")

    def test_01_enroll_and_dispatch(self):
        """Verifies candidate sequence enrollment and Touch 1 staging."""
        res = self.engine.enroll_and_dispatch(
            phone="-14156450879",
            message="Hey please reply , you one reply  means so much to me",
            name="Alex",
            interval_hours=24,
            max_touches=4
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["phone"], "+14156450879")
        self.assertEqual(res["stage"], 1)
        self.assertEqual(res["status"], "ACTIVE_WAITING_REPLY")

        status = self.engine.get_contact_status("+14156450879")
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "ACTIVE")
        self.assertEqual(status["current_stage"], 1)
        print("\n  [PASS] Sequence Enrollment: Contact enrolled with Touch 1 dispatched and status ACTIVE.")

    def test_02_reply_auto_halt(self):
        """Verifies that an incoming reply halts the sequence immediately."""
        self.engine.enroll_and_dispatch(
            phone="+14156450879",
            message="Hey please reply , you one reply  means so much to me",
        )
        # Simulate reply halt
        halted = self.engine.halt_sequence("+14156450879", reason="Inbound SMS reply detected")
        self.assertTrue(halted)

        status = self.engine.get_contact_status("+14156450879")
        self.assertEqual(status["status"], "REPLIED")
        self.assertNotIn("+14156450879", self.engine.get_active_phones())
        print("  [PASS] Auto-Halt on Reply: Sequence halted instantly and status changed to REPLIED.")

    def test_03_natural_language_command_parsing(self):
        """Verifies natural conversational phrasing in CommandEngine."""
        raw_cmd = "send a mssg to that number -14156450879 the mssg is -Hey please reply , you one reply  means so much to me"
        res = command_engine.execute(raw_cmd)
        self.assertTrue(res["success"])
        self.assertEqual(res["command"], "sms")
        self.assertEqual(res["result"]["recipient"], "14156450879")
        self.assertIn("Hey please reply", res["result"]["message"])
        print("  [PASS] Natural Language SMS: Parsed conversational request and formatted payload.")

    def test_04_natural_language_sequence_parsing(self):
        """Verifies natural sequence command parsing in CommandEngine."""
        raw_cmd = "repeat message to -14156450879 the mssg is -Hey please reply , you one reply  means so much to me"
        res = command_engine.execute(raw_cmd)
        self.assertTrue(res["success"])
        self.assertEqual(res["command"], "sequence")
        self.assertEqual(res["result"]["phone"], "+14156450879")
        self.assertEqual(res["result"]["stage"], 1)
        print("  [PASS] Natural Language Sequence: Parsed repeat command, enrolled contact, scheduled Touch 2.")


if __name__ == "__main__":
    unittest.main()
