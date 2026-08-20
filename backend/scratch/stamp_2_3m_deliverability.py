import os
import sys
import duckdb
import time
import json
import pandas as pd

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from scripts.run_deliverability_engine import MX_CACHE_PATH

print("=" * 80)
print("STAMPING DELIVERABILITY ACROSS ALL 2,303,300 RECORDS")
print("=" * 80)

# Load MX cache
with open(MX_CACHE_PATH, "r", encoding="utf-8") as f:
    mx_cache = json.load(f)
print(f"Loaded {len(mx_cache):,} cached domain validations.")

con = duckdb.connect()
domain_rows = [{"domain": d, "mx_valid": info.get("valid", False), "mx_type": info.get("type", "unknown")} for d, info in mx_cache.items()]
con.register("domain_reg", pd.DataFrame(domain_rows))

p2_3m = "C:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
if os.path.exists(p2_3m):
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p2_3m}')").fetchall()]
    print(f"Existing columns in 2.3M file ({len(cols)}):", cols)
    
    exclude_cols = [c for c in ['email_status', 'is_deliverable', 'email_confidence'] if c in cols]
    exclude_clause = f"EXCLUDE ({', '.join(exclude_cols)})" if exclude_cols else ""
    
    t0 = time.time()
    print("\nProcessing 2,303,300 raw archive dataset...")
    tmp_out = "C:/TalentOpsAI/backend/data/recruiters_full_cleaned.tmp.parquet"
    
    con.execute(f"""
    COPY (
        WITH classified AS (
            SELECT 
                r.* {exclude_clause},
                CASE 
                    WHEN r.email IS NULL OR r.email = '' OR r.email LIKE '%@missing.local%' THEN 'missing'
                    WHEN d.mx_type = 'disposable' THEN 'undeliverable'
                    WHEN d.mx_valid = false THEN 'undeliverable'
                    WHEN LOWER(SPLIT_PART(r.email, '@', 1)) IN ('info', 'admin', 'sales', 'support', 'contact', 'hr', 'jobs', 'careers', 'noreply', 'no-reply', 'billing', 'marketing', 'team', 'hello', 'recruiter') THEN 'risky_catchall'
                    WHEN d.mx_type = 'free_provider' THEN 'likely_deliverable'
                    WHEN d.mx_valid = true AND d.mx_type = 'corporate_mx' THEN 'verified'
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

                CASE 
                    WHEN r.email IS NULL OR r.email = '' OR r.email LIKE '%@missing.local%' THEN false
                    WHEN d.mx_type = 'disposable' OR d.mx_valid = false THEN false
                    ELSE true
                END AS is_deliverable
            FROM read_parquet('{p2_3m}') r
            LEFT JOIN domain_reg d ON LOWER(SPLIT_PART(r.email, '@', 2)) = d.domain
        )
        SELECT * FROM classified
    ) TO '{tmp_out}' (FORMAT PARQUET)
    """)
    
    stats_2_3m = con.execute(f"""
        SELECT email_status, is_deliverable, COUNT(*) as count, AVG(email_confidence) as avg_conf
        FROM read_parquet('{tmp_out}')
        GROUP BY 1, 2
        ORDER BY count DESC
    """).fetchdf()
    
    print("\n2,303,300 Dataset Deliverability Breakdown:")
    print(stats_2_3m.to_string())
    
    os.replace(tmp_out, p2_3m)
    print(f"\nSuccessfully stamped 2,303,300 records in {round(time.time() - t0, 2)}s!")

con.close()
