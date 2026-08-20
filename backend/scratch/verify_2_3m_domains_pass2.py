import json
import duckdb
import os

print("=" * 80)
print("CHECK 2 (PASS 2): DOMAIN REGISTRY MX COVERAGE ACROSS ALL 22,933 DOMAINS")
print("=" * 80)

MX_CACHE_PATH = r"C:\TalentOpsAI\backend\data\mx_domain_registry.json"
p2_3m = "C:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"

with open(MX_CACHE_PATH, "r", encoding="utf-8") as f:
    mx_cache = json.load(f)

print(f"[2.1] Total Domains in MX Registry: {len(mx_cache):,}")

con = duckdb.connect()
df_doms = con.execute(f"""
    SELECT DISTINCT LOWER(SPLIT_PART(email, '@', 2)) AS domain 
    FROM read_parquet('{p2_3m}')
    WHERE email IS NOT NULL AND email LIKE '%@%' AND email NOT LIKE '%@missing.local%'
""").fetchdf()

unique_domains = set([d for d in df_doms['domain'].tolist() if d and '.' in d])
print(f"[2.2] Unique Domains in 2.3M Dataset: {len(unique_domains):,}")

missing_in_registry = [d for d in unique_domains if d not in mx_cache]
print(f"[2.3] Domains Missing from MX Registry: {len(missing_in_registry)} (MUST BE 0)")
assert len(missing_in_registry) == 0, f"Missing {len(missing_in_registry)} domains from registry"

con.close()
print("\n" + "=" * 80)
print("CHECK 2 (PASS 2) RESULT: 100% DOMAIN MX RESOLUTION COVERAGE VERIFIED!")
print("=" * 80)
