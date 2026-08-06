"""
Company ID Reconciliation Engine — TalentOpsAI
Fixes the company_id field in recruiters_full.parquet by replacing string company names
with proper integer FK references to the Postgres companies table.

This script:
1. Extracts all distinct string company_ids from Parquet
2. Fuzzy-matches them against Postgres companies
3. Creates new companies for unmatched names
4. Uses email domain as a secondary mapping signal
5. Rewrites the Parquet file with corrected integer company_ids
6. Reloads DuckDB and uploads to Supabase
"""

import sys
import os
import re
import time
import shutil
import logging

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import duckdb
import pandas as pd
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.services.recruiter_store import PARQUET_FILE, recruiter_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconciler")

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

JUNK_NAMES = {
    "need to fill data", "unknown", "n/a", "na", "none", "tbd",
    "to be determined", "not available", "missing", "null", "",
    "nan", "test", "temp", "placeholder"
}

def is_junk_company_name(name_str):
    """Detect phone numbers, email addresses, person names, and other junk."""
    if not name_str:
        return True
    s = str(name_str).strip()
    low = s.lower()
    if low in JUNK_NAMES:
        return True
    if len(s) < 2:
        return True
    # Phone numbers: mostly digits, dashes, spaces, parens
    digits_only = re.sub(r'[^0-9]', '', s)
    if len(digits_only) >= 7 and len(digits_only) / max(len(s), 1) > 0.5:
        return True
    # Email addresses
    if '@' in s:
        return True
    # Looks like a person name (two words, both capitalized, no special chars)
    words = s.split()
    if len(words) == 2 and all(w[0].isupper() and w[1:].islower() for w in words if len(w) > 1):
        # Check if it looks like "First Last" — skip common company words
        company_indicators = {'inc', 'llc', 'corp', 'group', 'tech', 'global', 'staffing', 'systems', 'solutions', 'resources', 'consulting'}
        if not any(w.lower() in company_indicators for w in words):
            return True
    # Very long strings (probably concatenated junk)
    if len(s) > 100:
        return True
    # Pipe or semicolon separated (multi-value junk)
    if '|' in s or ';' in s:
        return True
    return False

WEBMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "protonmail.com", "ymail.com", "live.com",
    "msn.com", "comcast.net", "att.net", "verizon.net", "sbcglobal.net",
    "cox.net", "charter.net", "earthlink.net", "optonline.net",
    "missing.local", "example.com"
}

def normalize_company_name(name):
    """Normalize a company name for fuzzy matching."""
    if not name:
        return ""
    s = str(name).strip().lower()
    # Remove common suffixes
    for suffix in [", inc.", ", inc", " inc.", " inc", ", llc", " llc", ", ltd", " ltd",
                   " corp.", " corp", " co.", " co", " group", " staffing",
                   " solutions", " services", " consulting", " technologies"]:
        s = s.replace(suffix, "")
    # Remove non-alphanumeric
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def extract_domain(email):
    """Extract domain from an email address."""
    if not email or '@' not in str(email):
        return None
    return str(email).split('@')[-1].strip().lower()


# ──────────────────────────────────────────────
# Phase 1: Build Mappings
# ──────────────────────────────────────────────

def build_postgres_company_index():
    """Load all Postgres companies into a lookup index."""
    logger.info("Loading Postgres companies...")
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT company_id, company_name, normalized_company_name, website, email_pattern "
            "FROM companies WHERE is_active = true"
        )).fetchall()

    by_name = {}       # normalized_name -> company_id
    by_domain = {}     # email domain -> company_id
    id_to_name = {}    # company_id -> company_name

    for r in rows:
        cid, cname, norm_name, website, email_pattern = r
        id_to_name[cid] = cname

        # Index by normalized name
        key = normalize_company_name(cname)
        if key:
            by_name[key] = cid
        if norm_name:
            by_name[normalize_company_name(norm_name)] = cid

        # Index by domain from website
        if website:
            domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].strip().lower()
            if domain and domain not in WEBMAIL_DOMAINS:
                by_domain[domain] = cid

        # Index by email_pattern domain
        if email_pattern:
            ep_domain = extract_domain(email_pattern)
            if ep_domain and ep_domain not in WEBMAIL_DOMAINS:
                by_domain[ep_domain] = cid

    logger.info(f"Loaded {len(id_to_name)} companies, {len(by_name)} name keys, {len(by_domain)} domain keys")
    return by_name, by_domain, id_to_name


def extract_string_company_ids(con):
    """Get all distinct string (non-numeric) company_ids from Parquet."""
    logger.info("Extracting distinct string company_ids from Parquet...")
    rows = con.execute(f"""
        SELECT company_id, COUNT(*) as cnt
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
        WHERE TRY_CAST(company_id AS INTEGER) IS NULL
          AND company_id IS NOT NULL
        GROUP BY company_id
        ORDER BY cnt DESC
    """).fetchall()
    logger.info(f"Found {len(rows)} distinct string company_ids covering {sum(r[1] for r in rows):,} records")
    return rows


# ──────────────────────────────────────────────
# Phase 2: Match & Create Companies
# ──────────────────────────────────────────────

def match_string_to_company(name_str, by_name, by_domain):
    """Try to match a string company name to a Postgres company_id."""
    if not name_str:
        return None

    clean = str(name_str).strip()

    # Is it junk?
    if is_junk_company_name(clean):
        return None

    # Exact normalized match
    norm = normalize_company_name(clean)
    if norm in by_name:
        return by_name[norm]

    # Try domain-style match (if the string looks like a domain)
    if '.' in clean and ' ' not in clean:
        domain = clean.lower().replace("www.", "")
        if domain in by_domain:
            return by_domain[domain]

    return None


def create_missing_companies(unmatched_names, by_name):
    """Create Postgres companies for unmatched string company names using batch inserts."""
    logger.info(f"Creating companies for {len(unmatched_names)} unmatched names (batch mode)...")
    db = SessionLocal()
    new_mapping = {}
    created = 0

    # First pass: filter and deduplicate
    to_create = []  # list of (original_name_str, clean_name, normalized_name)
    seen_norms = set()
    for name_str, count in unmatched_names:
        clean = str(name_str).strip()
        if is_junk_company_name(clean):
            continue
        norm = normalize_company_name(clean)
        if norm in by_name:
            new_mapping[name_str] = by_name[norm]
            continue
        if norm in seen_norms:
            # Will be resolved after the first one creates a company
            continue
        seen_norms.add(norm)
        to_create.append((name_str, clean, norm))

    logger.info(f"  {len(to_create)} unique companies to create after dedup")

    try:
        BATCH = 200
        for i in range(0, len(to_create), BATCH):
            batch = to_create[i:i+BATCH]
            # Batch insert
            values_parts = []
            params = {}
            for j, (orig, clean, norm) in enumerate(batch):
                values_parts.append(f"(:name_{j}, :norm_{j}, true, 'reconciliation', NOW(), NOW())")
                params[f"name_{j}"] = clean
                params[f"norm_{j}"] = norm

            sql = (
                "INSERT INTO companies (company_name, normalized_company_name, is_active, data_source, created_at, updated_at) "
                "VALUES " + ", ".join(values_parts) + " "
                "ON CONFLICT DO NOTHING "
                "RETURNING company_id, company_name"
            )
            result = db.execute(text(sql), params)
            returned = result.fetchall()
            db.commit()

            # Build mapping from returned rows
            returned_by_name = {normalize_company_name(r[1]): r[0] for r in returned}
            for orig, clean, norm in batch:
                if norm in returned_by_name:
                    new_mapping[orig] = returned_by_name[norm]
                    by_name[norm] = returned_by_name[norm]
                    created += 1

            logger.info(f"  Batch {i//BATCH + 1}: created {len(returned)} companies (total: {created})")

        # Second pass: map any duplicates that matched the same normalized name
        for name_str, count in unmatched_names:
            if name_str in new_mapping:
                continue
            clean = str(name_str).strip()
            norm = normalize_company_name(clean)
            if norm in by_name:
                new_mapping[name_str] = by_name[norm]

        logger.info(f"Created {created} new companies in Postgres (batch mode)")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating companies: {e}")
        raise
    finally:
        db.close()

    return new_mapping


# ──────────────────────────────────────────────
# Phase 3: Build Email Domain → Company Mapping
# ──────────────────────────────────────────────

def build_email_domain_mapping(con, by_domain):
    """Build a mapping from email domain to company_id for records with NULL/junk company_id."""
    logger.info("Building email domain → company_id mapping from existing data...")

    # Also build from the Parquet data itself: for records that DO have valid numeric
    # company_ids, what email domains do they use?
    rows = con.execute(f"""
        SELECT SPLIT_PART(email, '@', 2) as domain,
               CAST(company_id AS INTEGER) as cid,
               COUNT(*) as cnt
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
        WHERE TRY_CAST(company_id AS INTEGER) IS NOT NULL
          AND email IS NOT NULL AND email LIKE '%@%'
        GROUP BY domain, cid
        ORDER BY cnt DESC
    """).fetchall()

    # For each domain, pick the company_id with the most records
    domain_counts = {}
    for domain, cid, cnt in rows:
        if not domain or domain.lower() in WEBMAIL_DOMAINS:
            continue
        domain_lower = domain.lower()
        if domain_lower not in domain_counts or cnt > domain_counts[domain_lower][1]:
            domain_counts[domain_lower] = (cid, cnt)

    for domain, (cid, cnt) in domain_counts.items():
        if domain not in by_domain:
            by_domain[domain] = cid

    logger.info(f"Email domain mapping now has {len(by_domain)} entries")
    return by_domain


# ──────────────────────────────────────────────
# Phase 4: Rewrite Parquet
# ──────────────────────────────────────────────

def rewrite_parquet(con, full_mapping, by_domain):
    """Rewrite the Parquet file with corrected company_ids."""
    logger.info("Reading entire Parquet into DuckDB for rewrite...")
    start = time.time()

    # Read the full Parquet
    df = con.execute(f"SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')").fetchdf()
    logger.info(f"Loaded {len(df):,} rows in {time.time()-start:.1f}s")

    # Build the fix
    fixed_count = 0
    junk_cleaned = 0
    domain_recovered = 0

    def fix_company_id(row):
        nonlocal fixed_count, junk_cleaned, domain_recovered
        cid = row['company_id']

        # Already a valid integer
        if cid is not None and pd.notna(cid):
            cid_str = str(cid)
            try:
                int_val = int(float(cid_str))
                # It's numeric — keep it
                return int_val
            except (ValueError, TypeError):
                pass

            # It's a string company name — look up mapping
            if cid_str in full_mapping:
                fixed_count += 1
                return full_mapping[cid_str]

            # Check if it's junk
            if cid_str.strip().lower() in JUNK_NAMES:
                junk_cleaned += 1
                # Try email domain recovery
                email = row.get('email')
                if email and '@' in str(email):
                    domain = str(email).split('@')[-1].strip().lower()
                    if domain in by_domain and domain not in WEBMAIL_DOMAINS:
                        domain_recovered += 1
                        return by_domain[domain]
                return None

            # Unknown string — try email domain
            email = row.get('email')
            if email and '@' in str(email):
                domain = str(email).split('@')[-1].strip().lower()
                if domain in by_domain and domain not in WEBMAIL_DOMAINS:
                    domain_recovered += 1
                    return by_domain[domain]
            return None
        else:
            # NULL company_id — try email domain recovery
            email = row.get('email')
            if email and '@' in str(email):
                domain = str(email).split('@')[-1].strip().lower()
                if domain in by_domain and domain not in WEBMAIL_DOMAINS:
                    domain_recovered += 1
                    return by_domain[domain]
            return None

    logger.info("Applying company_id fixes...")
    t1 = time.time()
    df['company_id'] = df.apply(fix_company_id, axis=1)
    logger.info(f"Applied fixes in {time.time()-t1:.1f}s")
    logger.info(f"  String names → FK: {fixed_count:,}")
    logger.info(f"  Junk cleaned: {junk_cleaned:,}")
    logger.info(f"  Email domain recovered: {domain_recovered:,}")

    # Cast company_id to proper integer (nullable)
    df['company_id'] = df['company_id'].astype('Int64')

    # Write back
    tmp_file = f"{PARQUET_FILE}.reconciled.tmp"
    logger.info("Writing reconciled Parquet file...")
    t2 = time.time()
    con2 = duckdb.connect()
    con2.register('df_fixed', df)
    con2.execute(f"COPY df_fixed TO '{tmp_file.replace(os.sep, '/')}' (FORMAT PARQUET, COMPRESSION 'ZSTD')")
    con2.close()
    logger.info(f"Written in {time.time()-t2:.1f}s")

    # Atomic swap
    shutil.move(tmp_file, PARQUET_FILE)
    logger.info("Atomic swap complete!")

    return fixed_count, junk_cleaned, domain_recovered


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    total_start = time.time()
    logger.info("=" * 70)
    logger.info("COMPANY ID RECONCILIATION ENGINE — TalentOpsAI")
    logger.info("=" * 70)

    con = duckdb.connect()

    # Phase 1: Build mappings
    by_name, by_domain, id_to_name = build_postgres_company_index()

    # Phase 1b: Email domain mapping from existing valid data
    by_domain = build_email_domain_mapping(con, by_domain)

    # Phase 1c: Extract string company_ids
    string_ids = extract_string_company_ids(con)

    # Phase 2: Match strings to existing companies
    full_mapping = {}   # string_name -> integer company_id
    unmatched = []

    for name_str, count in string_ids:
        matched_id = match_string_to_company(name_str, by_name, by_domain)
        if matched_id:
            full_mapping[name_str] = matched_id
        else:
            if str(name_str).strip().lower() not in JUNK_NAMES and len(str(name_str).strip()) >= 2:
                unmatched.append((name_str, count))

    matched_records = sum(c for n, c in string_ids if n in full_mapping)
    logger.info(f"Matched {len(full_mapping)} string names → existing companies ({matched_records:,} records)")
    logger.info(f"Unmatched: {len(unmatched)} company names")

    # Phase 2b: Create new companies for unmatched
    if unmatched:
        new_mapping = create_missing_companies(unmatched, by_name)
        full_mapping.update(new_mapping)
        logger.info(f"Total mapping now has {len(full_mapping)} entries")

    # Phase 3: Rewrite Parquet
    fixed, cleaned, recovered = rewrite_parquet(con, full_mapping, by_domain)
    con.close()

    # Phase 4: Reload
    logger.info("Reloading RecruiterStore...")
    recruiter_store.reload()

    # Verify
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION")
    logger.info("=" * 70)

    con2 = duckdb.connect()
    r = con2.execute(f"""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN company_id IS NOT NULL THEN 1 ELSE 0 END) as with_company,
            SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) as without_company
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
    """).fetchone()
    logger.info(f"Total: {r[0]:,}")
    logger.info(f"With company_id: {r[1]:,} ({r[1]/r[0]*100:.1f}%)")
    logger.info(f"Without company_id: {r[2]:,} ({r[2]/r[0]*100:.1f}%)")

    logger.info("\nTop 10 companies by recruiter count:")
    top = con2.execute(f"""
        SELECT company_id, COUNT(*) as cnt
        FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
        WHERE company_id IS NOT NULL
        GROUP BY company_id
        ORDER BY cnt DESC
        LIMIT 10
    """).fetchall()
    for row in top:
        cname = id_to_name.get(row[0], f"ID:{row[0]}")
        logger.info(f"  {cname} (id={row[0]}): {row[1]:,} recruiters")

    con2.close()
    
    elapsed = time.time() - total_start
    logger.info(f"\nReconciliation complete in {elapsed:.1f}s")
    logger.info(f"  String names resolved: {fixed:,}")
    logger.info(f"  Junk values cleaned: {cleaned:,}")
    logger.info(f"  Email domain recoveries: {recovered:,}")


if __name__ == "__main__":
    main()
