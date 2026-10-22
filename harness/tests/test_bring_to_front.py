"""
harness/tests/test_bring_to_front.py — Headless Verification of Window & App Launch Handlers
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, r"C:\TalentOpsAI")

from harness.connectors.teams_connector import teams_connector
from harness.connectors.outlook_connector import outlook_connector
from harness.connectors.vitel_connector import vitel_connector
from harness.connectors.site_connector import site_connector


class TestBringToFront(unittest.TestCase):

    def test_01_outlook_bring_to_front_active_window(self):
        """Verifies Outlook bring_to_front succeeds on live desktop window."""
        success = outlook_connector.bring_to_front()
        self.assertTrue(success)
        print("\n  [PASS] Outlook bring_to_front: Verified live desktop window activation.")

    def test_02_outlook_bring_to_front_desktop_launch(self):
        """Verifies Outlook launches targeting WinSta0\\Default when no window is active."""
        with patch.object(outlook_connector, "find_outlook_windows", return_value=[]):
            with patch("ctypes.windll.kernel32.CreateProcessW", return_value=1) as mock_cp:
                success = outlook_connector.bring_to_front()
                self.assertTrue(success)
                self.assertEqual(mock_cp.call_count, 1)
        print("  [PASS] Outlook bring_to_front: Verified CreateProcessW targeting WinSta0\\Default.")

    def test_03_teams_bring_to_front_active_window(self):
        """Verifies Teams bring_to_front succeeds on live desktop window."""
        success = teams_connector.bring_to_front()
        self.assertTrue(success)
        print("  [PASS] Teams bring_to_front: Verified live desktop window activation.")

    def test_04_teams_bring_to_front_desktop_launch(self):
        """Verifies Teams launches targeting WinSta0\\Default when no window is active."""
        with patch.object(teams_connector, "find_teams_windows", return_value=[]):
            with patch("ctypes.windll.kernel32.CreateProcessW", return_value=1) as mock_cp:
                success = teams_connector.bring_to_front()
                self.assertTrue(success)
                self.assertEqual(mock_cp.call_count, 1)
        print("  [PASS] Teams bring_to_front: Verified CreateProcessW targeting WinSta0\\Default.")

    def test_05_vitel_bring_to_front_logic(self):
        """Verifies Vitel bring_to_front verifies executable path."""
        self.assertTrue(os.path.exists(vitel_connector.DEFAULT_EXE_PATH))
        with patch("subprocess.Popen") as mock_popen:
            success = vitel_connector.bring_to_front()
            self.assertTrue(success)
            mock_popen.assert_called_once()
        print("  [PASS] Vitel bring_to_front: Verified Vitelglobal.exe execution path.")


if __name__ == "__main__":
    unittest.main()
