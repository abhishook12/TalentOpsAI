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

    def test_01_outlook_bring_to_front_logic(self):
        """Verifies Outlook bring_to_front triggers MAPI Explorer Display."""
        mock_app = MagicMock()
        mock_ns = MagicMock()
        mock_inbox = MagicMock()
        mock_app.Explorers.Count = 0
        mock_ns.GetDefaultFolder.return_value = mock_inbox

        with patch.object(outlook_connector, "_get_com_session", return_value=(mock_app, mock_ns)):
            success = outlook_connector.bring_to_front()
            self.assertTrue(success)
            mock_inbox.Display.assert_called_once()
        print("\n  [PASS] Outlook bring_to_front: Verified MAPI Inbox.Display() called when Explorers.Count == 0.")

    def test_02_teams_bring_to_front_logic(self):
        """Verifies Teams bring_to_front triggers native protocol and AppExecutionAlias."""
        with patch("ctypes.windll.shell32.ShellExecuteW", return_value=42) as mock_shell:
            success = teams_connector.bring_to_front()
            self.assertTrue(success)
            self.assertGreater(mock_shell.call_count, 0)
        print("  [PASS] Teams bring_to_front: Verified ShellExecuteW protocol dispatch.")

    def test_03_vitel_bring_to_front_logic(self):
        """Verifies Vitel bring_to_front verifies executable path."""
        self.assertTrue(os.path.exists(vitel_connector.DEFAULT_EXE_PATH))
        with patch("subprocess.Popen") as mock_popen:
            success = vitel_connector.bring_to_front()
            self.assertTrue(success)
            mock_popen.assert_called_once()
        print("  [PASS] Vitel bring_to_front: Verified Vitelglobal.exe execution path.")


if __name__ == "__main__":
    unittest.main()
