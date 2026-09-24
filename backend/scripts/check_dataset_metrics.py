import duckdb

con = duckdb.connect()
q = """
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN recruiter_name ILIKE '% via %' THEN 1 END) as via_names,
    COUNT(CASE WHEN recruiter_name ILIKE '% dba %' THEN 1 END) as dba_names,
    COUNT(CASE WHEN recruiter_name ILIKE '%docusign%' THEN 1 END) as docusign_names,
    COUNT(CASE WHEN email ILIKE '%@googlegroups.com%' THEN 1 END) as googlegroups_emails,
    COUNT(CASE WHEN recruiter_name LIKE '%"%' OR recruiter_name LIKE '%''%' THEN 1 END) as quote_names,
    COUNT(CASE WHEN is_active = true AND (email IS NULL OR email = '' OR email = 'None') THEN 1 END) as missing_emails,
    COUNT(CASE WHEN is_active = true AND (state IS NULL OR TRIM(state) = '' OR LOWER(state) = 'nan') THEN 1 END) as missing_states,
    COUNT(CASE WHEN sentinel_status = 'swept_clean' THEN 1 END) as swept_clean_count
FROM read_parquet('backend/data/recruiters_full.parquet')
"""
res = con.execute(q).fetchone()
cols = ["total", "via_names", "dba_names", "docusign_names", "googlegroups_emails", "quote_names", "missing_emails", "missing_states", "swept_clean_count"]
for c, val in zip(cols, res):
    print(f"{c}: {val:,}")
