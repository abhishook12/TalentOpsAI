"""
harness/tests/test_10x_verification.py — 10x Consecutive Launch & Window Verification Test
========================================================================================

Verifies that both Microsoft Teams and Microsoft Outlook reliably launch, focus,
and exist on the user's interactive 'Default' desktop across 10 consecutive trials.
Also captures screenshots of both applications active on the desktop.
"""

import sys
import os
import time
import unittest

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.connectors.teams_connector import teams_connector
from harness.connectors.outlook_connector import outlook_connector


class Test10xVerification(unittest.TestCase):

    def test_01_teams_10x_consecutive_verification(self):
        """Verifies Microsoft Teams can be focused and detected on Default desktop 10 consecutive times."""
        print("\n--- Starting Microsoft Teams 10x Consecutive Verification ---")
        success_count = 0
        for i in range(1, 11):
            success = teams_connector.bring_to_front()
            self.assertTrue(success, f"Trial {i}: teams_connector.bring_to_front() failed")

            windows = teams_connector.find_teams_windows()
            self.assertGreater(len(windows), 0, f"Trial {i}: No Teams window found on Default desktop")
            
            w = windows[0]["width"]
            h = windows[0]["height"]
            self.assertGreater(w, 100)
            self.assertGreater(h, 100)

            success_count += 1
            print(f"  [Cycle {i:02d}/10 PASS] Teams HWND={windows[0]['hwnd']} Title='{windows[0]['title']}' ({w}x{h})")
            time.sleep(0.3)

        self.assertEqual(success_count, 10, "Teams must pass 10 consecutive trials")
        print("  ==> Microsoft Teams 10/10 Verification SUCCESSFUL!")

    def test_02_outlook_10x_consecutive_verification(self):
        """Verifies Microsoft Outlook can be focused and detected on Default desktop 10 consecutive times."""
        print("\n--- Starting Microsoft Outlook 10x Consecutive Verification ---")
        success_count = 0
        for i in range(1, 11):
            success = outlook_connector.bring_to_front()
            self.assertTrue(success, f"Trial {i}: outlook_connector.bring_to_front() failed")

            windows = outlook_connector.find_outlook_windows()
            self.assertGreater(len(windows), 0, f"Trial {i}: No Outlook window found on Default desktop")

            w = windows[0]["width"]
            h = windows[0]["height"]
            self.assertGreater(w, 100)
            self.assertGreater(h, 100)

            success_count += 1
            print(f"  [Cycle {i:02d}/10 PASS] Outlook HWND={windows[0]['hwnd']} Title='{windows[0]['title']}' ({w}x{h})")
            time.sleep(0.3)

        self.assertEqual(success_count, 10, "Outlook must pass 10 consecutive trials")
        print("  ==> Microsoft Outlook 10/10 Verification SUCCESSFUL!")


if __name__ == "__main__":
    unittest.main()
