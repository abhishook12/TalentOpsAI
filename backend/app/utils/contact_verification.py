from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .normalizer import extract_domain, normalize_text
from .phone_normalizer import phone_compare_key

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


def _normalize_email(value: Any) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


def _normalize_phone(value: Any) -> str:
    if not value:
        return ""
    return phone_compare_key(value)


def _normalize_linkedin(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = text.replace("https://", "").replace("http://", "")
    text = text.replace("www.", "")
    text = text.rstrip("/")
    return text


def _flatten_metadata(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"value": value}
    return {"value": value}


def _parse_csv_values(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    if not text.strip():
        return []
    return [part.strip() for part in re.split(r"[,\n;|]+", text) if part.strip()]


def _company_key(company_id: Any, company_name: Any, company_normalized_name: Any = None) -> str:
    if company_id not in (None, ""):
        return f"id:{company_id}"
    if company_normalized_name:
        return f"name:{normalize_text(company_normalized_name)}"
    if company_name:
        return f"name:{normalize_text(company_name)}"
    return ""


@dataclass
class ContactCluster:
    indices: set[int] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)
    strong_signals: set[str] = field(default_factory=set)


def build_contact_fingerprints(recruiter: Any, company_name: str | None = None, company_normalized_name: str | None = None) -> dict[str, Any]:
    metadata = _flatten_metadata(getattr(recruiter, "metadata_json", None))
    emails = []
    phones = []
    linkedins = []

    for field_name in ("email", "email2", "email3", "email4"):
        emails.append(getattr(recruiter, field_name, None))
    for field_name in ("phone", "phone2", "phone3", "phone4"):
        phones.append(getattr(recruiter, field_name, None))

    emails.extend(_parse_csv_values(metadata.get("all_emails")))
    emails.extend(_parse_csv_values(metadata.get("extra_emails")))
    phones.extend(_parse_csv_values(metadata.get("all_phones")))
    phones.extend(_parse_csv_values(metadata.get("extra_phones")))

    if getattr(recruiter, "linkedin", None):
        linkedins.append(getattr(recruiter, "linkedin"))
    linkedins.extend(_parse_csv_values(metadata.get("linkedin")))
    linkedins.extend(_parse_csv_values(metadata.get("linkedins")))

    normalized_emails = []
    for email in emails:
        norm = _normalize_email(email)
        if norm and norm not in normalized_emails:
            normalized_emails.append(norm)

    normalized_phones = []
    for phone in phones:
        norm = _normalize_phone(phone)
        if norm and norm not in normalized_phones:
            normalized_phones.append(norm)

    normalized_linkedins = []
    for linkedin in linkedins:
        norm = _normalize_linkedin(linkedin)
        if norm and norm not in normalized_linkedins:
            normalized_linkedins.append(norm)

    name = normalize_text(getattr(recruiter, "recruiter_name", None))
    company_key_value = _company_key(
        getattr(recruiter, "company_id", None),
        company_name,
        company_normalized_name,
    )

    fingerprints: dict[str, Any] = {
        "name": name,
        "company_key": company_key_value,
        "emails": normalized_emails,
        "phones": normalized_phones,
        "linkedins": normalized_linkedins,
        "metadata": metadata,
        "raw_email_domain": extract_domain(emails[0]) if emails else "",
    }
    return fingerprints


def build_duplicate_keys(fingerprints: dict[str, Any]) -> dict[str, set[str]]:
    keys = defaultdict(set)
    recruiter_id = fingerprints.get("recruiter_id")
    base = f"r:{recruiter_id}" if recruiter_id is not None else "r:unknown"

    for email in fingerprints.get("emails", []):
        if email:
            keys["email"].add(f"email:{email}")
    for phone in fingerprints.get("phones", []):
        if phone:
            keys["phone"].add(f"phone:{phone}")
    for linkedin in fingerprints.get("linkedins", []):
        if linkedin:
            keys["linkedin"].add(f"linkedin:{linkedin}")

    name = fingerprints.get("name") or ""
    company_key = fingerprints.get("company_key") or ""
    if name and company_key:
        keys["name_company"].add(f"name_company:{name}:{company_key}")

    if name:
        keys["name"].add(f"name:{name}")
    if company_key:
        keys["company"].add(f"company:{company_key}")
    if fingerprints.get("raw_email_domain"):
        domain = fingerprints["raw_email_domain"]
        if domain and domain not in GENERIC_EMAIL_DOMAINS:
            keys["domain"].add(f"domain:{domain}")

    keys["base"].add(base)
    return keys


def confidence_for_cluster(cluster: ContactCluster) -> str:
    strong_signals = cluster.get("strong_signals") if isinstance(cluster, dict) else cluster.strong_signals
    index_count = len(cluster.get("indices", [])) if isinstance(cluster, dict) else len(cluster.indices)
    distinct_names = int(cluster.get("distinct_names", 0)) if isinstance(cluster, dict) else 0
    distinct_companies = int(cluster.get("distinct_companies", 0)) if isinstance(cluster, dict) else 0
    distinct_emails = int(cluster.get("distinct_emails", 0)) if isinstance(cluster, dict) else 0
    distinct_phones = int(cluster.get("distinct_phones", 0)) if isinstance(cluster, dict) else 0
    if strong_signals & {"email", "phone", "linkedin"}:
        if index_count <= 10 and distinct_names <= 3 and distinct_companies <= 3 and (distinct_emails <= 2 or distinct_phones <= 2):
            return "high"
        if index_count <= 50 and distinct_names <= 10 and distinct_companies <= 10:
            return "medium"
        return "low"
    if "name_company" in strong_signals and index_count >= 2:
        if distinct_names <= 3 and distinct_companies <= 3 and index_count <= 10:
            return "medium"
        return "low"
    if "domain" in strong_signals and index_count >= 2:
        return "low"
    return "low"


def summarize_cluster(cluster_id: int, cluster: ContactCluster, records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}

    strong_signals = cluster.get("strong_signals") if isinstance(cluster, dict) else cluster.strong_signals
    distinct_names = {normalize_text(record.get("recruiter_name")) for record in records if normalize_text(record.get("recruiter_name"))}
    distinct_companies = {normalize_text(record.get("company_name")) for record in records if normalize_text(record.get("company_name"))}
    distinct_states = {str(record.get("state")).strip().upper() for record in records if str(record.get("state") or "").strip()}
    distinct_emails = {_normalize_email(record.get("email")) for record in records if _normalize_email(record.get("email"))}
    distinct_phones = {re.sub(r"\D+", "", str(record.get("phone") or "")) for record in records if re.sub(r"\D+", "", str(record.get("phone") or ""))}

    canonical = max(
        records,
        key=lambda record: (
            int(record.get("completeness_score") or 0),
            int(record.get("trust_score") or 0),
            1 if record.get("is_active") else 0,
            1 if record.get("state") else 0,
            -(record.get("recruiter_id") or 0),
        ),
    )
    confidence = confidence_for_cluster(cluster)
    return {
        "cluster_id": cluster_id,
        "size": len(records),
        "confidence": confidence,
        "strong_signals": sorted(strong_signals),
        "canonical_recruiter_id": canonical.get("recruiter_id"),
        "canonical_name": canonical.get("recruiter_name"),
        "canonical_email": canonical.get("email"),
        "canonical_company": canonical.get("company_name"),
        "distinct_names": len(distinct_names),
        "distinct_companies": len(distinct_companies),
        "distinct_states": len(distinct_states),
        "distinct_emails": len(distinct_emails),
        "distinct_phones": len(distinct_phones),
        "members": [
            {
                "recruiter_id": record.get("recruiter_id"),
                "recruiter_name": record.get("recruiter_name"),
                "email": record.get("email"),
                "phone": record.get("phone"),
                "linkedin": record.get("linkedin"),
                "company_name": record.get("company_name"),
                "state": record.get("state"),
            }
            for record in records
        ],
    }
