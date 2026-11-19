"""Resolve person fields without using browser or company-page titles as facts."""
import re
from ..utils.normalizer import clean_company, clean_location_text, is_platform_name
from .interface_labels import interface_label

_WORK_MODE = r"(?:remote|hybrid|on[- ]?site|work from home)"
_PAGE_LABEL = re.compile(r"^(?:our team|meet (?:our|the) team|careers|jobs|about us)\s*[-–—:|]", re.I)


def person_location(raw):
    location = clean_location_text(raw)
    if not location or interface_label(location):
        return None
    location = re.sub(rf"\s*(?:\({_WORK_MODE}\)|[|·,]\s*{_WORK_MODE})$", "", location, flags=re.I).strip()
    if not location or re.fullmatch(rf"{_WORK_MODE}(?:[\s/,]+(?:or\s+)?{_WORK_MODE})*(?: jobs?)?", location, re.I):
        return None
    return location


def person_employer(record):
    headline = record.raw_title or ""
    first_clause = re.split(r"[|•·]", headline, maxsplit=1)[0]
    match = re.search(r"\s+(?:at\s+|@\s*)([^@|]+)$", first_clause, re.I)
    if match and not re.search(r"\b(?:formerly|previously|former|ex)[- ]", first_clause, re.I):
        value = clean_company(match[1])
        if value and not is_platform_name(value) and not _PAGE_LABEL.match(value):
            return value, "headline", first_clause
    raw = (record.raw_company or "").strip()
    if not raw or interface_label(raw) or _PAGE_LABEL.match(raw) or raw.casefold() == (record.source_page_title or "").strip().casefold():
        return None, None, None
    value = clean_company(raw)
    return (value, "company_field", raw) if value and not is_platform_name(value) else (None, None, None)


def field_evidence(record, value, section, excerpt):
    seen = getattr(record, "created_at", None)
    return {"value": value, "section": section, "excerpt": excerpt,
            "source_url": record.source_url, "capture_id": record.capture_id,
            "seen_at": seen.isoformat() if seen else None}
