"""
TalentOps Scout 2.0 - Data Loss Prevention (DLP) & Privacy Engine
Local pre-upload scanning and redaction of credentials, API keys,
tokens, credit cards, and private secrets.
"""

from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("scout.security.dlp")


@dataclass
class DLPFinding:
    pattern_name: str
    redacted_preview: str
    start_pos: int
    end_pos: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_name": self.pattern_name,
            "redacted_preview": self.redacted_preview,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }


class DLPEngine:
    """
    Scans and redacts sensitive data locally on the Scout edge node
    before observations are queued, persisted, or synced to the backend.
    """

    PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        # AWS Access Key
        ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        # OpenAI / Stripe / General Secret Keys
        ("GENERIC_SECRET_KEY", re.compile(r"\b(?:sk_live_|sk_test_|sk-)[a-zA-Z0-9_-]{20,}\b")),
        # GitHub Personal Access Token
        ("GITHUB_TOKEN", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
        ("GITHUB_PAT", re.compile(r"\bgithub_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}\b")),
        # Slack Token
        ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,}\b")),
        # Bearer Authorization Token
        ("BEARER_TOKEN", re.compile(r"(?i)\bbearer\s+([a-zA-Z0-9_\-\.]{20,})\b")),
        # Common key-value secrets (e.g. password="xxx", api_key='yyy')
        ("KEY_VALUE_SECRET", re.compile(r"(?i)\b(password|passwd|secret|api_key|auth_token|private_key)\s*[:=]\s*[\"']?([^\s\"',;}{]{6,})[\"']?")),
        # Credit Card Numbers (13-16 digits formatted)
        ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
        # Private Key block
        ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z\s]+PRIVATE KEY-----[^-]+-----END [A-Z\s]+PRIVATE KEY-----")),
    ]

    REDACTION_STRING = "[REDACTED_SECRET]"

    @classmethod
    def scan_text(cls, text: str) -> list[DLPFinding]:
        """Inspect text for sensitive patterns and return matches."""
        if not text or not isinstance(text, str):
            return []

        findings: list[DLPFinding] = []
        for name, pattern in cls.PATTERNS:
            for match in pattern.finditer(text):
                val = match.group(0)
                preview = val[:4] + "..." + val[-2:] if len(val) > 6 else "[REDACTED]"
                findings.append(DLPFinding(
                    pattern_name=name,
                    redacted_preview=preview,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        return findings

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Scan text and replace all sensitive secrets with [REDACTED_SECRET]."""
        if not text or not isinstance(text, str):
            return text

        result = text
        for name, pattern in cls.PATTERNS:
            if name == "KEY_VALUE_SECRET":
                # Only redact the secret value part to maintain key readability
                def replace_kv(match: re.Match[str]) -> str:
                    key = match.group(1)
                    return f"{key}={cls.REDACTION_STRING}"
                result = pattern.sub(replace_kv, result)
            elif name == "BEARER_TOKEN":
                result = pattern.sub(f"Bearer {cls.REDACTION_STRING}", result)
            else:
                result = pattern.sub(cls.REDACTION_STRING, result)

        return result

    @classmethod
    def redact_dict(cls, data: Any) -> Any:
        """
        Recursively traverse dicts, lists, and primitives, redacting any secrets.
        """
        if isinstance(data, dict):
            clean_dict: dict[str, Any] = {}
            for k, v in data.items():
                # If key explicitly indicates a secret or credential, mask value directly
                if any(sec in k.lower() for sec in ["password", "secret", "token", "private_key", "api_key"]):
                    if isinstance(v, str) and v:
                        clean_dict[k] = cls.REDACTION_STRING
                        continue
                clean_dict[k] = cls.redact_dict(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls.redact_dict(item) for item in data]
        elif isinstance(data, str):
            return cls.redact_text(data)
        else:
            return data

    @classmethod
    def is_safe(cls, data: Any) -> bool:
        """
        Returns True if no sensitive patterns are found.
        """
        if isinstance(data, str):
            return len(cls.scan_text(data)) == 0
        elif isinstance(data, dict):
            for k, v in data.items():
                if any(sec in str(k).lower() for sec in ["password", "private_key", "secret"]):
                    if v and str(v) != cls.REDACTION_STRING:
                        return False
                if not cls.is_safe(v):
                    return False
            return True
        elif isinstance(data, list):
            return all(cls.is_safe(item) for item in data)
        return True
