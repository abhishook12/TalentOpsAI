from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Iterable

from .normalizer import extract_domain
from .state_mapper import extract_state_detailed

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "msn.com",
    "live.com",
    "proton.me",
    "protonmail.com",
}


def flatten_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except Exception:
        text = str(value).strip()
        return text or None

    parts: list[str] = []

    def walk(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, dict):
            for nested in item.values():
                walk(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                walk(nested)
            return
        text = str(item).strip()
        if text:
            parts.append(text)

    walk(parsed)
    return " ".join(parts) if parts else None


def is_generic_domain(domain: str | None) -> bool:
    if not domain:
        return True
    return domain.lower() in GENERIC_EMAIL_DOMAINS


def build_company_domain_state_index(companies: Iterable[Any]) -> dict[str, dict[str, set[Any]]]:
    index: dict[str, dict[str, set[Any]]] = defaultdict(lambda: {"states": set(), "company_ids": set()})
    for company in companies:
        company_id = getattr(company, "company_id", None)
        company_state = getattr(company, "state", None)
        for source in (getattr(company, "website", None), getattr(company, "email_pattern", None)):
            domain = extract_domain(source)
            if not domain or is_generic_domain(domain):
                continue
            bucket = index[domain]
            if company_id is not None:
                bucket["company_ids"].add(company_id)
            if company_state:
                bucket["states"].add(company_state)
    return index


def infer_state_from_domain(value: str | None, domain_index: dict[str, dict[str, set[Any]]]) -> tuple[str | None, str | None, str | None]:
    if not value:
        return None, None, None
    domain = extract_domain(value)
    if not domain or is_generic_domain(domain):
        return None, None, None
    info = domain_index.get(domain)
    if not info:
        return None, None, None
    states = sorted(info["states"])
    if len(states) == 1:
        return states[0], "domain_single_state", f"domain:{domain}"
    if len(states) > 1:
        return None, "domain_conflict", f"domain:{domain}"
    return None, None, None


def infer_state_from_sources(
    sources: list[tuple[str, Any]],
    *,
    domain_index: dict[str, dict[str, set[Any]]] | None = None,
) -> dict[str, Any] | None:
    for source_label, source_value in sources:
        if not source_value:
            continue
        if source_label == "email_domain" and domain_index:
            state, reason, evidence = infer_state_from_domain(source_value, domain_index)
            if state:
                return {
                    "state": state,
                    "state_source": "email_domain",
                    "state_confidence": "medium",
                    "state_reason": reason,
                    "evidence": evidence,
                }
            continue

        flattened = flatten_text(source_value)
        if not flattened:
            continue
        state, reason = extract_state_detailed(flattened)
        if not state:
            continue
        if source_label in {"recruiter_location", "company_location", "company_state"}:
            confidence = "high"
        elif source_label in {"notes", "review_reason", "metadata_json", "raw_data"}:
            confidence = "medium"
        else:
            confidence = "low"
        return {
            "state": state,
            "state_source": source_label,
            "state_confidence": confidence,
            "state_reason": reason,
            "evidence": flattened[:500],
        }

    return None
