import sys
import os
import time
import duckdb

sys.path.insert(0, r"C:\TalentOpsAI\backend")

PARQUET_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"

print("=" * 70)
print("TEST SUITE 1: COMPREHENSIVE DATA INTEGRITY & ENRICHMENT AUDIT")
print("=" * 70)

conn = duckdb.connect()

# 1. Total Count Verification
total_rows = conn.execute(f"SELECT COUNT(*) FROM '{PARQUET_PATH}'").fetchone()[0]
print(f"[TEST 1.1] Total Parquet Rows: {total_rows:,}")
assert total_rows >= 2303315, f"Expected at least 2,303,315 rows, got {total_rows}"
print("  --> PASS: Total rows invariant verified.\n")

# 2. BridgeCross, LLC Ingestion Verification
bc_rows = conn.execute(f"""
    SELECT recruiter_id, recruiter_name, email, company_id, is_deliverable, quality_score, is_active
    FROM '{PARQUET_PATH}'
    WHERE LOWER(COALESCE(company_id, '')) LIKE '%bridgecross%' 
       OR LOWER(COALESCE(email, '')) LIKE '%bridgecross%'
    ORDER BY recruiter_name
""").fetchall()

print(f"[TEST 1.2] BridgeCross, LLC Ingested Contacts: {len(bc_rows)} records found")
assert len(bc_rows) >= 15, f"Expected at least 15 BridgeCross contacts, got {len(bc_rows)}"

expected_names = [
    "Danny Collins", "Natia Mgebrishvili", "Suman B.", "Riley Devaul",
    "Sankar Subramanian", "Margie Collins", "Calvin Hsu", "Kelly T.",
    "Bryan Pham", "Barbara Lanza", "Matt Starr", "Jagadesh Yellapu"
]
found_names = [r[1] for r in bc_rows]
for exp in expected_names:
    assert any(exp.lower() in fn.lower() for fn in found_names), f"Missing contact: {exp}"
    print(f"  [OK] Verified contact: {exp}")

print("  --> PASS: All BridgeCross roster members verified in database.\n")

# 3. MX Deliverability & Data Quality Verification
valid_mx_count = conn.execute(f"""
    SELECT COUNT(*) FROM '{PARQUET_PATH}' 
    WHERE is_deliverable = TRUE
""").fetchone()[0]
avg_quality = conn.execute(f"""
    SELECT AVG(quality_score) FROM '{PARQUET_PATH}' 
    WHERE quality_score > 0
""").fetchone()[0]

print(f"[TEST 1.3] Data Quality Metrics:")
print(f"  - Total MX Verified Deliverable: {valid_mx_count:,} ({(valid_mx_count/total_rows)*100:.2f}%)")
print(f"  - Average Quality Score: {avg_quality:.2f}%")
assert valid_mx_count > 2000000, "Deliverable count below threshold"
print("  --> PASS: Data quality invariants verified.\n")

# 4. State Aggregation & Coverage Audit
state_counts = conn.execute(f"""
    SELECT UPPER(COALESCE(state, 'UNKNOWN')) AS st, COUNT(*) AS cnt
    FROM '{PARQUET_PATH}'
    GROUP BY 1
    ORDER BY cnt DESC
""").fetchall()

print(f"[TEST 1.4] Geographic Coverage Audit:")
print(f"  - Total Distinct State Buckets: {len(state_counts)}")
unknown_count = next((cnt for st, cnt in state_counts if st in ('UNKNOWN', '')), 0)
print(f"  - Unknown State Records: {unknown_count}")
print(f"  - Top 5 States by Density:")
for st, cnt in state_counts[:5]:
    print(f"      {st}: {cnt:,} recruiters")

assert unknown_count == 0, f"Found {unknown_count} unmapped state records!"
assert len(state_counts) >= 50, f"Expected at least 50 US states, got {len(state_counts)}"
print("  --> PASS: 100% US Geographic coverage verified with 0 unmapped records.\n")

# 5. Fuzzy Company Search & Smart Resolution Audit
from app.services.recruiter_store import recruiter_store

test_queries = [
    ("bridgecross", "bridgecrossllc"),
    ("BridgeCross, LLC", "bridgecrossllc"),
    ("brdgcross", "bridgecrossllc"),
    ("insight", "insight"),
    ("Insight Global", "insightglobal"),
    ("aerotek", "aerotek"),
    ("Teksystems", "teksystems")
]

print(f"[TEST 1.5] Fuzzy Company Search Benchmarks:")
for q, exp_key in test_queries:
    t0 = time.time()
    results = recruiter_store.company_directory(query=q)
    dur_ms = (time.time() - t0) * 1000
    top = results[0] if results else {}
    top_name = top.get("company_key", "")
    top_domain = top.get("dominant_domain", "")
    print(f"  - Query: '{q}' -> Top Match: '{top_name}' ({top_domain}) | {top.get('recruiter_count', 0)} recruiters | {dur_ms:.1f}ms")
    
    clean_name = str(top_name).lower().replace(" ", "").replace(",", "").replace("-", "")
    clean_domain = str(top_domain or "").lower().replace(" ", "").replace(",", "").replace("-", "")
    matched = exp_key in clean_name or exp_key in clean_domain
    assert matched, f"Failed fuzzy match for '{q}', got '{top_name}' ({top_domain})"

print("  --> PASS: All fuzzy and typo-tolerant search benchmarks passed.\n")

print("=" * 70)
print("ALL DATA INTEGRITY AND RECRUITER INGESTION TESTS PASSED 100%!")
print("=" * 70)
