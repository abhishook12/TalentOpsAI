"""
utils/negative_patterns.py — Persistent Negative Reviewer Feedback Pattern Registry

Stores user-defined "Never accept this pattern" rules across:
- company (e.g. bogus employer names, ATS names, UI labels)
- name (e.g. non-person names, UI action buttons)
- title (e.g. generic system roles)
- url (e.g. blacklisted domains or patterns)

Learns continuously from reviewer feedback to filter out repeat noise.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("talentops.negative_patterns")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
PATTERNS_FILE = os.path.join(DATA_DIR, "negative_patterns.json")

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
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_PATTERNS, f, indent=2)
            return list(DEFAULT_PATTERNS)
        except Exception as e:
            logger.warning("Failed to initialize negative patterns file: %s", e)
            return list(DEFAULT_PATTERNS)
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read negative patterns: %s", e)
        return list(DEFAULT_PATTERNS)


def _save_patterns(patterns: List[Dict[str, Any]]) -> bool:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2)
        return True
    except Exception as e:
        logger.error("Failed to save negative patterns: %s", e)
        return False


def add_negative_pattern(pattern: str, pattern_type: str = "company", reason: Optional[str] = None) -> bool:
    """Adds a new negative pattern submitted by human reviewer."""
    clean_p = pattern.strip().lower()
    if not clean_p:
        return False

    patterns = _load_patterns()
    for item in patterns:
        if item.get("pattern", "").lower() == clean_p and item.get("type", "").lower() == pattern_type.lower():
            return True  # Already registered

    patterns.append({
        "pattern": clean_p,
        "type": pattern_type.lower(),
        "reason": reason or "Manually flagged as 'Never accept this pattern' by reviewer",
    })
    return _save_patterns(patterns)


def get_negative_patterns(pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all registered negative patterns, optionally filtered by type."""
    patterns = _load_patterns()
    if pattern_type:
        p_type = pattern_type.lower()
        return [p for p in patterns if p.get("type", "").lower() == p_type]
    return patterns


def is_blacklisted_pattern(value: Optional[str], pattern_type: str = "company") -> bool:
    """Checks whether a value matches any registered negative pattern."""
    if not value or not isinstance(value, str):
        return False
    val_low = value.strip().lower()
    patterns = get_negative_patterns(pattern_type)
    for p in patterns:
        pat = p.get("pattern", "").lower()
        if pat == val_low or (len(pat) >= 4 and pat in val_low):
            return True
    return False
