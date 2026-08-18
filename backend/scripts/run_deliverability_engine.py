import sys
import os
import time
import json
import socket
import asyncio
import re
import duckdb
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import PARQUET_FILE, recruiter_store
from app.database import SessionLocal
from app.models.models import Recruiter

MX_CACHE_PATH = r"C:\TalentOpsAI\backend\data\mx_domain_registry.json"

FREE_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com',
    'live.com', 'msn.com', 'comcast.net', 'att.net', 'sbcglobal.net', 'verizon.net',
    'me.com', 'mail.com', 'protonmail.com', 'ymail.com', 'cox.net', 'charter.net',
    'googlemail.com', 'yahoo.co.uk', 'hotmail.co.uk', 'zoho.com', 'gmx.com'
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "yopmail.com", "10minutemail.com", 
    "tempmail.com", "throwaway.email", "temp-mail.org", "sharklasers.com",
    "spam4.me", "fakemail.net", "dispostable.com", "trashmail.com",
    "tempmailaddress.com", "getairmail.com", "emailondeck.com", "tempmail.net",
    "mintemail.com", "maildrop.cc", "tempmail.co.com", "mytrashmail.com",
    "spamgourmet.com", "jetable.org", "incognitomail.com", "anonbox.net",
    "spambog.com", "0clickemail.com", "tempail.com", "mailexpire.com"
}

ROLE_PREFIXES = {
    "info", "admin", "sales", "support", "contact", "hr", "jobs", 
    "careers", "noreply", "no-reply", "billing", "marketing", "team", 
    "hello", "webmaster", "postmaster", "hostmaster", "abuse", "recruiter", "talent"
}

try:
    import dns.resolver
    import dns.asyncresolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

async def check_mx_domain(domain: str, semaphore: asyncio.Semaphore, cache: dict) -> tuple:
    if domain in cache:
        return domain, cache[domain]
        
    if domain in FREE_DOMAINS:
        res = {"valid": True, "type": "free_provider", "host": "major_provider"}
        cache[domain] = res
        return domain, res

    if domain in DISPOSABLE_DOMAINS:
        res = {"valid": False, "type": "disposable", "host": None}
        cache[domain] = res
        return domain, res
        
    async with semaphore:
        loop = asyncio.get_running_loop()
        try:
            if HAS_DNSPYTHON:
                try:
                    answers = await dns.asyncresolver.resolve(domain, 'MX', lifetime=2.5)
                    mx_host = str(answers[0].exchange).rstrip('.')
                    res = {"valid": True, "type": "corporate_mx", "host": mx_host}
                    cache[domain] = res
                    return domain, res
                except Exception:
                    pass
                    
            # Fallback to standard DNS socket resolution
            addrinfo = await loop.getaddrinfo(domain, 80, family=socket.AF_INET, type=socket.SOCK_STREAM)
            if addrinfo:
                res = {"valid": True, "type": "domain_a_record", "host": addrinfo[0][4][0]}
                cache[domain] = res
                return domain, res
        except Exception:
            pass
            
    res = {"valid": False, "type": "unresolvable", "host": None}
    cache[domain] = res
    return domain, res

async def resolve_all_domains(unique_domains: list, mx_cache: dict) -> dict:
    print(f"[*] Resolving MX records for {len(unique_domains):,} domains...")
    semaphore = asyncio.Semaphore(150)
    tasks = []
    
    for dom in unique_domains:
        tasks.append(check_mx_domain(dom, semaphore, mx_cache))
        
    # Run in batches of 2000
    batch_size = 2000
    for i in range(0, len(tasks), batch_size):
        chunk = tasks[i:i + batch_size]
        await asyncio.gather(*chunk)
        print(f"    -> Resolved {min(i + batch_size, len(tasks)):,} / {len(tasks):,} domains ({round((min(i + batch_size, len(tasks)) / len(tasks)) * 100, 1)}%)")
        
    return mx_cache

def run_deliverability_pipeline():
    start_time = time.time()
    print("=" * 80)
    print("ENTERPRISE DELIVERABILITY & MAIL VERIFIER ENGINE")
    print("=" * 80)

    # 1. Load Parquet dataset and extract unique domains
    print("\n[Step 1/5] Extracting domains from Parquet dataset...")
    con = duckdb.connect()
    pq_clean = PARQUET_FILE.replace(os.sep, '/')
    
    df_domains = con.execute(f"""
        SELECT DISTINCT LOWER(SPLIT_PART(email, '@', 2)) AS domain 
        FROM read_parquet('{pq_clean}')
        WHERE email IS NOT NULL AND email LIKE '%@%' AND email NOT LIKE '%@missing.local%'
    """).fetchdf()
    
    unique_domains = [d for d in df_domains['domain'].tolist() if d and '.' in d]
    print(f"    -> Extracted {len(unique_domains):,} unique corporate & personal domains.")

    # 2. Load existing cache or resolve MX records
    print("\n[Step 2/5] Performing Asynchronous DNS MX Resolution...")
    mx_cache = {}
    if os.path.exists(MX_CACHE_PATH):
        try:
            with open(MX_CACHE_PATH, "r", encoding="utf-8") as f:
                mx_cache = json.load(f)
            print(f"    -> Loaded {len(mx_cache):,} cached domain records from {MX_CACHE_PATH}.")
        except Exception as e:
            print(f"    -> Error loading MX cache: {e}")

    domains_to_resolve = [d for d in unique_domains if d not in mx_cache]
    if domains_to_resolve:
        print(f"    -> Resolving {len(domains_to_resolve):,} new domains...")
        mx_cache = asyncio.run(resolve_all_domains(domains_to_resolve, mx_cache))
        os.makedirs(os.path.dirname(MX_CACHE_PATH), exist_ok=True)
        with open(MX_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(mx_cache, f)
        print(f"    -> Saved updated MX cache with {len(mx_cache):,} domains.")
    else:
        print("    -> All domains already present in high-speed MX cache.")

    # 3. Vectorized Deliverability Classification & Parquet Transformation
    print("\n[Step 3/5] Executing Vectorized Deliverability Classification across 421k+ records...")
    
    # Create temporary table for domain registry inside DuckDB
    domain_rows = []
    for d, info in mx_cache.items():
        domain_rows.append({
            "domain": d,
            "mx_valid": info.get("valid", False),
            "mx_type": info.get("type", "unknown"),
            "mx_host": info.get("host")
        })
    df_domain_registry = pd.DataFrame(domain_rows)
    con.register("domain_reg", df_domain_registry)

    # Perform high-speed vectorized classification
    now_iso = datetime.now(timezone.utc).isoformat()
    tmp_output = f"{PARQUET_FILE}.tmp_deliverability_{int(time.time())}.parquet"
    tmp_output_clean = tmp_output.replace(os.sep, '/')

    transform_sql = f"""
    COPY (
        WITH classified AS (
            SELECT 
                r.recruiter_id,
                r.recruiter_name,
                r.normalized_recruiter_name,
                r.email,
                r.phone,
                r.email2,
                r.phone2,
                r.email3,
                r.phone3,
                r.email4,
                r.phone4,
                r.alternate_emails,
                r.alternate_phones,
                r.linkedin,
                r.specialization,
                r.title,
                r.notes,
                r.review_reason,
                r.company_id,
                r.location,
                r.state,
                r.normalized_city,
                r.location_confidence,
                r.state_source,
                r.state_confidence,
                r.state_reason,
                r.last_scan_at,
                r.completeness_score,
                r.needs_review,
                r.is_active,
                r.data_source,
                r.trust_score,
                r.source_job_id,
                r.raw_data,
                r.metadata_json,
                r.tags,
                r.created_at,
                r.updated_at,
                r.taxonomy_category,
                r.report_count,
                
                -- NEW STANDARDIZED DELIVERABILITY FIELDS --
                CASE 
                    -- Missing / synthetic placeholder
                    WHEN r.email IS NULL OR r.email = '' OR r.email LIKE '%@missing.local%' THEN 'missing'
                    -- Disposable domain
                    WHEN d.mx_type = 'disposable' THEN 'undeliverable'
                    -- Dead / Unresolvable domain
                    WHEN d.mx_valid = false THEN 'undeliverable'
                    -- Role accounts
                    WHEN LOWER(SPLIT_PART(r.email, '@', 1)) IN ('info', 'admin', 'sales', 'support', 'contact', 'hr', 'jobs', 'careers', 'noreply', 'no-reply', 'billing', 'marketing', 'team', 'hello', 'recruiter') THEN 'risky_catchall'
                    -- Personal email provider (Gmail, Yahoo, Outlook)
                    WHEN d.mx_type = 'free_provider' THEN 'likely_deliverable'
                    -- Verified corporate MX
                    WHEN d.mx_valid = true AND d.mx_type = 'corporate_mx' THEN 'verified'
                    -- Fallback A record
                    WHEN d.mx_valid = true THEN 'likely_deliverable'
                    ELSE 'likely_deliverable'
                END AS email_status,

                CASE 
                    WHEN r.email IS NULL OR r.email = '' OR r.email LIKE '%@missing.local%' THEN 0
                    WHEN d.mx_type = 'disposable' OR d.mx_valid = false THEN 0
                    WHEN LOWER(SPLIT_PART(r.email, '@', 1)) IN ('info', 'admin', 'sales', 'support', 'contact', 'hr', 'jobs', 'careers', 'noreply', 'no-reply', 'billing', 'marketing', 'team', 'hello', 'recruiter') THEN 60
                    WHEN d.mx_type = 'free_provider' THEN 80
                    WHEN d.mx_valid = true AND d.mx_type = 'corporate_mx' THEN 95
                    WHEN d.mx_valid = true THEN 75
                    ELSE 70
                END AS email_confidence,

                'Deliverability Engine v2.0' AS email_source,
                r.email_pattern_id,
                r.email_generated,
                '{now_iso}' AS email_verified_at,
                '{now_iso}' AS email_last_checked_at,
                r.canonical_company_id,
                r.historical_company_id,
                r.company_domain_id,
                r.raw_email_value,
                r.repair_reason,
                r.user_id,
                r.quality_score,
                r.missing_fields,
                r.sentinel_status,
                r.last_verified_at,
                r.company_confidence,
                r.company_reasoning,
                r.is_archived,
                r.merged_into_id,
                r.logo_url,
                
                -- STRICT DELIVERABILITY BOOLEAN --
                CASE 
                    WHEN r.email IS NULL OR r.email = '' OR r.email LIKE '%@missing.local%' THEN false
                    WHEN d.mx_type = 'disposable' OR d.mx_valid = false THEN false
                    ELSE true
                END AS is_deliverable,
                
                r.seniority_level,
                r.timezone_code,
                r.timezone,
                r.company_scale
            FROM read_parquet('{pq_clean}') r
            LEFT JOIN domain_reg d ON LOWER(SPLIT_PART(r.email, '@', 2)) = d.domain
        )
        SELECT * FROM classified
    ) TO '{tmp_output_clean}' (FORMAT PARQUET)
    """
    
    con.execute(transform_sql)
    
    # 4. Verification of Temporary File before Atomic Swap
    stats_df = con.execute(f"""
        SELECT 
            email_status,
            is_deliverable,
            COUNT(*) as count,
            AVG(email_confidence) as avg_confidence
        FROM read_parquet('{tmp_output_clean}')
        GROUP BY 1, 2
        ORDER BY count DESC
    """).fetchdf()
    
    print("\n[Step 4/5] Transformed Parquet Deliverability Metrics:")
    print(stats_df.to_string())
    
    # Assert zero missing emails marked as deliverable
    missing_deliverable_cnt = con.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{tmp_output_clean}')
        WHERE (email IS NULL OR email = '' OR email LIKE '%@missing.local%') AND is_deliverable = true
    """).fetchone()[0]
    
    assert missing_deliverable_cnt == 0, f"Critical error: {missing_deliverable_cnt} missing emails are marked deliverable!"
    
    con.close()
    
    # Atomic Swap
    if os.path.exists(PARQUET_FILE):
        backup_file = f"{PARQUET_FILE}.bak_deliverability"
        if os.path.exists(backup_file):
            os.remove(backup_file)
        os.rename(PARQUET_FILE, backup_file)
        
    os.rename(tmp_output, PARQUET_FILE)
    print(f"\n    -> Successfully performed atomic swap for {PARQUET_FILE}.")

    # 5. Reload Unified RecruiterStore
    print("\n[Step 5/5] Reloading Unified RecruiterStore in-memory query engine...")
    recruiter_store.reload()
    print("    -> RecruiterStore reloaded.")

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"DELIVERABILITY PIPELINE COMPLETED IN {duration}s!")
    print("=" * 80)

if __name__ == "__main__":
    run_deliverability_pipeline()
