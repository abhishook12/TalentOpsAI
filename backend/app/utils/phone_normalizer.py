from __future__ import annotations

import re
from typing import Any

EXTENSION_RE = re.compile(r"(?:\bext\.?\b|\bextension\b|\bx\b|#)\s*\d+\s*$", re.I)


def strip_phone_extension(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return EXTENSION_RE.sub("", text).strip()


def extract_phone_digits(value: Any) -> str:
    text = strip_phone_extension(value)
    if not text:
        return ""
    return re.sub(r"\D+", "", text)


def normalize_us_phone_digits(value: Any) -> str:
    digits = extract_phone_digits(value)
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def format_us_phone(value: Any) -> str | None:
    digits = normalize_us_phone_digits(value)
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    text = strip_phone_extension(value)
    return text or None


def phone_compare_key(value: Any) -> str:
    digits = normalize_us_phone_digits(value)
    return digits

