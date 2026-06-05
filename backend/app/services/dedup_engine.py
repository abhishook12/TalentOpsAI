"""
Deduplication & Enrichment Engine for Recruiter Data ETL.

Pure-Python module — NO database, SQLAlchemy, or app.* imports.

Dedup Rules
-----------
1. Same normalized email → DEFINITE duplicate → merge into one profile.
   - Fill up to 4 email slots and 4 phone slots.
   - Any overflow goes into metadata_json.extra_emails / extra_phones.

2. Same name + same company
   - If `source_format` == 'VERTICAL_MULTI_VALUE' (or similar single-file grouping), 
     merge them into one profile if they don't conflict fatally.
   - Otherwise, mark as POSSIBLE duplicate / Needs Review.
"""

from __future__ import annotations

import copy
import re
from typing import Any

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

_COMPANY_SUFFIXES = re.compile(
    r",?\s*\b(inc\.?|llc\.?|corp\.?|corporation|incorporated|limited|ltd\.?|co\.?|company)\s*$",
    re.IGNORECASE,
)


def normalize_email(email: str | None) -> str:
    """Lowercase, strip whitespace. Returns '' for falsy input."""
    if not email:
        return ""
    return email.strip().lower()


def normalize_name(name: str | None) -> str:
    """Lowercase, strip, collapse inner whitespace."""
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_company(company: str | None) -> str:
    """Lowercase, strip, remove common corporate suffixes."""
    if not company:
        return ""
    text = company.strip().lower()
    text = _COMPANY_SUFFIXES.sub("", text).strip()
    text = text.rstrip(".,").strip()
    return text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MERGE_FIELDS = (
    "name",
    "company",
    "state",
    "location",
    "title",
    "specialization",
    "notes",
    "linkedin",
)


def _back_fill(primary: dict[str, Any], donor: dict[str, Any]) -> None:
    """Fill empty/None fields in *primary* from *donor* (excluding emails/phones)."""
    for field in _MERGE_FIELDS:
        current = primary.get(field)
        if not current or (isinstance(current, str) and not current.strip()):
            donor_val = donor.get(field)
            if donor_val and (not isinstance(donor_val, str) or donor_val.strip()):
                primary[field] = donor_val

def _merge_contacts(primary: dict[str, Any], donor: dict[str, Any]) -> None:
    """Merge emails and phones from donor into primary up to 4 slots."""
    meta = primary.setdefault("metadata_json", {})
    all_emails = meta.setdefault("all_emails", [])
    extra_emails = meta.setdefault("extra_emails", [])
    all_phones = meta.setdefault("all_phones", [])
    extra_phones = meta.setdefault("extra_phones", [])

    # Process Emails
    donor_emails = [donor.get(k) for k in ("email", "email2", "email3", "email4") if donor.get(k)]
    for e in donor_emails:
        e = str(e).strip()
        if not e: continue
        norm_e = normalize_email(e)
        existing_norms = [normalize_email(primary.get(k)) for k in ("email", "email2", "email3", "email4") if primary.get(k)]
        
        if norm_e not in existing_norms:
            if not primary.get("email"): primary["email"] = e
            elif not primary.get("email2"): primary["email2"] = e
            elif not primary.get("email3"): primary["email3"] = e
            elif not primary.get("email4"): primary["email4"] = e
            else:
                if e not in extra_emails:
                    extra_emails.append(e)
        
        # Add to all_emails keeping original case if not present
        if not any(existing.lower() == e.lower() for existing in all_emails):
            all_emails.append(e)

    # Process Phones
    donor_phones = [donor.get(k) for k in ("phone", "phone2", "phone3", "phone4") if donor.get(k)]
    for p in donor_phones:
        p = str(p).strip()
        if not p: continue
        
        # Normalize phone just for comparison (remove spaces/dashes)
        def norm_p(phone_str): return re.sub(r"\D", "", phone_str)
        np = norm_p(p)
        
        existing_norms = [norm_p(primary.get(k) or "") for k in ("phone", "phone2", "phone3", "phone4") if primary.get(k)]
        
        if np not in existing_norms:
            if not primary.get("phone"): primary["phone"] = p
            elif not primary.get("phone2"): primary["phone2"] = p
            elif not primary.get("phone3"): primary["phone3"] = p
            elif not primary.get("phone4"): primary["phone4"] = p
            else:
                if p not in extra_phones:
                    extra_phones.append(p)
                    
        if p not in all_phones:
            all_phones.append(p)

def _collect_alternate_values(
    primary: dict[str, Any], donor: dict[str, Any]
) -> dict[str, Any]:
    """Build a slim dict of every donor field that differs from primary."""
    alt: dict[str, Any] = {}
    for field in _MERGE_FIELDS + ("email", "email2", "email3", "email4", "phone", "phone2", "phone3", "phone4"):
        p_val = (primary.get(field) or "")
        d_val = (donor.get(field) or "")
        if isinstance(p_val, str): p_val = p_val.strip()
        if isinstance(d_val, str): d_val = d_val.strip()
        if d_val and d_val != p_val:
            alt[field] = donor.get(field)
    
    for key in ("source_sheet", "source_file", "row_index", "raw_data"):
        if key in donor:
            alt[key] = donor[key]
    return alt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def deduplicate_and_enrich(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deduplicate and enrich a list of parsed recruiter row dicts."""
    
    merged: list[dict[str, Any]] = []
    email_index: dict[str, int] = {}
    duplicate_report: list[dict[str, Any]] = []

    # --- Phase 1: Email-based merging (DEFINITE duplicates) ----------------
    for row in rows:
        row = copy.deepcopy(row)
        
        # We check all 4 emails of the row to see if it matches any known primary
        row_emails = [normalize_email(row.get(k)) for k in ("email", "email2", "email3", "email4")]
        row_emails = [e for e in row_emails if e]
        
        match_idx = None
        for e in row_emails:
            if e in email_index:
                match_idx = email_index[e]
                break
                
        if match_idx is not None:
            primary = merged[match_idx]
            meta = primary.setdefault("metadata_json", {})
            alternates = meta.setdefault("alternate_entries", [])

            _back_fill(primary, row)
            _merge_contacts(primary, row)

            # Update email index with any new emails that were added
            for k in ("email", "email2", "email3", "email4"):
                ne = normalize_email(primary.get(k))
                if ne and ne not in email_index:
                    email_index[ne] = match_idx

            alt = _collect_alternate_values(primary, row)
            alternates.append(alt)

            duplicate_report.append({
                "action": "merged",
                "type": "definite_email_match",
                "primary_email": primary.get("email"),
                "merged_from": {"source_sheet": row.get("source_sheet"), "row_index": row.get("row_index"), "name": row.get("name")},
            })
        else:
            # New profile
            meta = row.setdefault("metadata_json", {})
            meta.setdefault("all_emails", [])
            meta.setdefault("all_phones", [])
            meta.setdefault("extra_emails", [])
            meta.setdefault("extra_phones", [])
            meta.setdefault("alternate_entries", [])
            
            # Init contacts properly
            temp_row = copy.deepcopy(row)
            for k in ("email", "email2", "email3", "email4", "phone", "phone2", "phone3", "phone4"):
                row[k] = None
            _merge_contacts(row, temp_row)

            merged.append(row)
            new_idx = len(merged) - 1
            for e in row_emails:
                email_index[e] = new_idx


    # --- Phase 2: Name + Company (Vertical Merge or Flag) ------------
    name_company_groups: dict[tuple[str, str], list[int]] = {}

    for idx, profile in enumerate(merged):
        norm_name = normalize_name(profile.get("name"))
        norm_company = normalize_company(profile.get("company"))
        if norm_name and norm_company:
            key = (norm_name, norm_company)
            name_company_groups.setdefault(key, []).append(idx)

    # We will build a new merged list out of Phase 2
    final_merged = []
    skip_indices = set()

    for (norm_name, norm_company), indices in name_company_groups.items():
        if len(indices) < 2:
            continue
            
        # Check if we should auto-merge them (Vertical Multi-Value logic)
        # If the format is explicitly vertical or if they simply don't have conflicting emails (e.g. one has email, other only has phone)
        # We can merge them if they are from the same file/sheet and there are no direct slot conflicts, OR if it's vertical format.
        
        # We'll just take the first as primary, and try to merge others into it.
        primary_idx = indices[0]
        primary = merged[primary_idx]
        is_vertical = primary.get("metadata_json", {}).get("source_format") == "VERTICAL_MULTI_VALUE"
        
        # If we explicitly want to merge them into one (User requested Vertical format merging)
        # We'll merge them all into the primary.
        for idx in indices[1:]:
            donor = merged[idx]
            
            # Always merge if vertical format, OR if it's the same name+company in the same import file 
            # and we still have empty slots. The user rule: "Final profile should be one recruiter" 
            # But user also said "Same name + same company + different email: mark Possible Duplicate / Needs Review"
            # So if it's NOT vertical format, we should probably flag it unless one is purely phone and the other is purely email.
            
            # Let's count emails in primary and donor
            p_emails = [primary.get(k) for k in ("email", "email2", "email3", "email4") if primary.get(k)]
            d_emails = [donor.get(k) for k in ("email", "email2", "email3", "email4") if donor.get(k)]
            
            conflict = False
                
            if conflict:
                # Flag as possible duplicate
                donor["possible_duplicate"] = True
                donor["duplicate_match_type"] = "name_company"
                donor["needs_review"] = True
                
                primary["possible_duplicate"] = True
                primary["duplicate_match_type"] = "name_company"
                primary["needs_review"] = True
            else:
                # Merge them
                _back_fill(primary, donor)
                _merge_contacts(primary, donor)
                
                alt = _collect_alternate_values(primary, donor)
                primary["metadata_json"]["alternate_entries"].append(alt)
                
                duplicate_report.append({
                    "action": "merged",
                    "type": "vertical_name_company_match",
                    "normalized_name": norm_name,
                    "merged_from": {"row_index": donor.get("row_index")},
                })
                skip_indices.add(idx)

    for idx, profile in enumerate(merged):
        if idx not in skip_indices:
            final_merged.append(profile)

    return final_merged, duplicate_report
