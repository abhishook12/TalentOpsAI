"""
harness/tests/test_command_api.py — REST API & CLI Execution Verification
"""
import sys
import os
import json
import subprocess
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, r"C:\TalentOpsAI")

from backend.app.routes.harness import router


class TestCommandApi(unittest.TestCase):

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_01_api_post_command(self):
        """Verifies POST /command executes commands and returns structured task receipts."""
        resp = self.client.post("/command", json={"command": "status"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["command"], "status")
        self.assertIn("summary", data["result"])
        print("\n  [PASS] POST /command: Successfully executed via REST API.")

    def test_02_cli_terminal_execution(self):
        """Verifies CLI execution from terminal (python -m harness.cli)."""
        res = subprocess.run(
            ["python", "-m", "harness.cli", "status"],
            cwd=r"C:\TalentOpsAI",
            capture_output=True,
            text=True,
            timeout=15
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["success"])
        self.assertEqual(data["command"], "status")
        print("  [PASS] CLI Terminal Invocation: python -m harness.cli 'status' verified.")

    def test_03_interactive_console_in_ui(self):
        """Verifies the interactive Command Console elements are rendered in the HTML UI."""
        resp = self.client.get("/ui")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Interactive Command & Task Console", resp.text)
        self.assertIn("cmdInput", resp.text)
        self.assertIn("runCommand()", resp.text)
        print("  [PASS] Interactive UI Console: Form elements, input box, and quick chips verified.")


if __name__ == "__main__":
    unittest.main()
