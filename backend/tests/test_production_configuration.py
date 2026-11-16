"""Regression tests for production configuration guardrails."""

import os
import subprocess
import sys


def _import_config(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_rejects_weak_credentials():
    result = _import_config(
        {"ENV": "production", "JWT_SECRET": "short", "ADMIN_PASSWORD": "short"}
    )
    assert result.returncode != 0
    assert "strong JWT_SECRET" in result.stderr


def test_production_accepts_sufficiently_strong_credentials():
    result = _import_config(
        {"ENV": "production", "JWT_SECRET": "a" * 48, "ADMIN_PASSWORD": "b" * 16}
    )
    assert result.returncode == 0, result.stderr
