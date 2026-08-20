import duckdb
import os
import time

parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full.parquet"
conn = duckdb.connect()

print("--- PARQUET DATASET DEEP PROFILE ---")
conn.execute(f"CREATE VIEW recs AS SELECT * FROM '{parquet_path}'")

total = conn.execute("SELECT COUNT(*) FROM recs").fetchone()[0]
print(f"Total Records: {total:,}")

# Field completeness
print("\n--- FIELD COMPLETENESS & QUALITY ---")
check_fields = [
    "recruiter_name", "email", "phone", "title", "company_id", "state", 
    "normalized_city", "location", "linkedin", "seniority_level", 
    "timezone", "taxonomy_category", "completeness_score", "quality_score"
]
for col in check_fields:
    filled = conn.execute(f"SELECT COUNT(*) FROM recs WHERE {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) != ''").fetchone()[0]
    pct = (filled / total) * 100
    print(f"  {col:<22}: {filled:>7,} / {total:,} ({pct:5.1f}% filled)")

# Email validation stats
print("\n--- EMAIL HEALTH BREAKDOWN ---")
valid_emails = conn.execute("SELECT COUNT(*) FROM recs WHERE email IS NOT NULL AND regexp_matches(email, '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')").fetchone()[0]
print(f"  Valid Syntax Emails  : {valid_emails:>7,} ({(valid_emails/total)*100:.1f}%)")

# Extract domain from email
print("\n--- EXTRACTED DOMAIN CARDINALITY ---")
unique_domains = conn.execute("SELECT COUNT(DISTINCT regexp_extract(email, '@(.*)$', 1)) FROM recs WHERE email IS NOT NULL").fetchone()[0]
print(f"  Unique Email Domains : {unique_domains:,}")

top_domains = conn.execute("SELECT regexp_extract(email, '@(.*)$', 1) as dom, COUNT(*) as cnt FROM recs WHERE email IS NOT NULL GROUP BY dom ORDER BY cnt DESC LIMIT 10").fetchall()
print("\n--- TOP 10 SENDER / COMPANY DOMAINS ---")
for d, cnt in top_domains:
    print(f"  {d:<30}: {cnt:,} recruiters")

# Seniority Level Distribution
print("\n--- SENIORITY LEVEL DISTRIBUTION ---")
seniority = conn.execute("SELECT seniority_level, COUNT(*) as cnt FROM recs GROUP BY seniority_level ORDER BY cnt DESC LIMIT 10").fetchall()
for s, cnt in seniority:
    print(f"  {str(s):<25}: {cnt:,} recruiters")

# Taxonomy Distribution
print("\n--- TAXONOMY CATEGORY DISTRIBUTION ---")
tax = conn.execute("SELECT taxonomy_category, COUNT(*) as cnt FROM recs GROUP BY taxonomy_category ORDER BY cnt DESC LIMIT 10").fetchall()
for t, cnt in tax:
    print(f"  {str(t):<25}: {cnt:,} recruiters")

# Top 10 States
print("\n--- TOP 10 STATES ---")
top_states = conn.execute("SELECT state, COUNT(*) as cnt FROM recs WHERE state IS NOT NULL GROUP BY state ORDER BY cnt DESC LIMIT 10").fetchall()
for s, cnt in top_states:
    print(f"  {str(s):<20}: {cnt:,} recruiters")

# Query Benchmarking
print("\n--- DUCKDB QUERY PERFORMANCE BENCHMARKS ---")
queries = [
    ("Full Scan Count", "SELECT COUNT(*) FROM recs"),
    ("Filter by State (TX)", "SELECT COUNT(*) FROM recs WHERE state = 'TX'"),
    ("Fuzzy Keyword Search ('engineer')", "SELECT * FROM recs WHERE title ILIKE '%engineer%' LIMIT 50"),
    ("Multi-filter Search (State + Title + Seniority)", "SELECT * FROM recs WHERE state = 'CA' AND title ILIKE '%Recruiter%' AND seniority_level = 'Senior' LIMIT 50"),
    ("Domain Aggregation Drilldown", "SELECT regexp_extract(email, '@(.*)$', 1) as dom, COUNT(*) as cnt FROM recs GROUP BY dom ORDER BY cnt DESC LIMIT 20"),
]

for label, q in queries:
    t0 = time.time()
    res = conn.execute(q).fetchall()
    dt = (time.time() - t0) * 1000
    print(f"  {label:<45}: {dt:6.2f} ms ({len(res)} rows)")
