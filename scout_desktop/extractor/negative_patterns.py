"""
extractor/negative_patterns.py — Client-Side Negative Pattern Registry

Synchronized with backend reviewer feedback rules:
Filters out names, companies, and titles that human reviewers marked "Never accept this pattern".
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("scout.negative_patterns")

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cache"))
PATTERNS_FILE = os.path.join(CACHE_DIR, "negative_patterns.json")

DEFAULT_PATTERNS = [
    {"pattern": "active window", "type": "company", "reason": "Desktop window tracker artifact"},
    {"pattern": "candidate card", "type": "company", "reason": "UI component artifact"},
    {"pattern": "quick search", "type": "company", "reason": "UI search box label"},
    {"pattern": "guided search", "type": "company", "reason": "LinkedIn UI filter label"},
    {"pattern": "turboscribe", "type": "company", "reason": "Audio transcription tool artifact"},
    {"pattern": "chatgpt", "type": "company", "reason": "AI assistant application"},
    {"pattern": "gemini", "type": "company", "reason": "AI assistant application"},
]


def _load_patterns() -> List[Dict[str, Any]]:
    if not os.path.exists(PATTERNS_FILE):
        return list(DEFAULT_PATTERNS)
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug("Failed reading negative patterns: %s", e)
        return list(DEFAULT_PATTERNS)


def add_negative_pattern(pattern: str, pattern_type: str = "company", reason: Optional[str] = None) -> bool:
    clean_p = pattern.strip().lower()
    if not clean_p:
        return False
    patterns = _load_patterns()
    for item in patterns:
        if item.get("pattern", "").lower() == clean_p and item.get("type", "").lower() == pattern_type.lower():
            return True
    patterns.append({
        "pattern": clean_p,
        "type": pattern_type.lower(),
        "reason": reason or "Marked 'Never accept this pattern'",
    })
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2)
        return True
    except Exception as e:
        logger.debug("Failed saving negative pattern: %s", e)
        return False


def is_blacklisted_pattern(value: Optional[str], pattern_type: str = "company") -> bool:
    if not value or not isinstance(value, str):
        return False
    val_low = value.strip().lower()
    patterns = _load_patterns()
    for p in patterns:
        if p.get("type", "").lower() == pattern_type.lower():
            pat = p.get("pattern", "").lower()
            if pat == val_low or (len(pat) >= 4 and pat in val_low):
                return True
    return False


# Alias for compatibility
is_pattern_blacklisted = is_blacklisted_pattern

