import duckdb
import json

con = duckdb.connect(':memory:')
path = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"

print("=" * 80)
print("COMPREHENSIVE ANOMALY AUDIT ACROSS 2,303,300 RECORDS")
print("=" * 80)

audit_sql = f"""
WITH analyzed AS (
    SELECT
        recruiter_id,
        recruiter_name,
        email,
        company_id,
        state,
        normalized_city,
        phone,
        title,
        -- Email checks
        CASE WHEN email IS NULL OR TRIM(email) = '' OR email LIKE '%@missing.local%' THEN 1 ELSE 0 END AS is_missing_email,
        CASE WHEN email LIKE '%@%' AND NOT regexp_matches(LOWER(TRIM(email)), '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$') THEN 1 ELSE 0 END AS is_malformed_email,
        
        -- Name checks
        CASE WHEN recruiter_name IS NULL OR TRIM(recruiter_name) = '' THEN 1 ELSE 0 END AS is_missing_name,
        CASE WHEN regexp_matches(TRIM(recruiter_name), '^[A-Z]\\.\\s+[A-Z][a-z]+$') THEN 1 ELSE 0 END AS is_initial_pattern_name,
        CASE WHEN LOWER(TRIM(recruiter_name)) IN ('recruiter', 'hr', 'admin', 'unknown', 'professional', 'talent', 'n/a', 'none', 'null') THEN 1 ELSE 0 END AS is_placeholder_name,
        
        -- City / State checks
        CASE WHEN normalized_city IS NULL OR TRIM(normalized_city) = '' OR LOWER(TRIM(normalized_city)) IN ('n/a', 'none', 'null', 'unknown') THEN 1 ELSE 0 END AS is_missing_city,
        CASE WHEN LOWER(TRIM(normalized_city)) = LOWER(TRIM(state)) 
                  OR LOWER(TRIM(normalized_city)) IN ('wisconsin', 'california', 'texas', 'florida', 'new york', 'illinois', 'ohio', 'michigan', 'georgia', 'north carolina', 'virginia', 'washington', 'arizona', 'massachusetts', 'tennessee', 'indiana', 'missouri', 'maryland', 'colorado', 'minnesota', 'south carolina', 'alabama', 'louisiana', 'kentucky', 'oregon', 'oklahoma', 'connecticut', 'utah', 'iowa', 'nevada', 'arkansas', 'mississippi', 'kansas', 'new mexico', 'nebraska', 'idaho', 'west virginia', 'hawaii', 'new hampshire', 'maine', 'montana', 'rhode island', 'delaware', 'south dakota', 'north dakota', 'alaska', 'vermont', 'wyoming') THEN 1 ELSE 0 END AS is_city_equals_state_name,
        CASE WHEN normalized_city LIKE '%,%' THEN 1 ELSE 0 END AS is_city_has_comma,
        
        -- Title checks
        CASE WHEN title IS NULL OR TRIM(title) = '' OR LOWER(TRIM(title)) IN ('n/a', 'none', 'null', 'unknown', 'professional') THEN 1 ELSE 0 END AS is_generic_or_missing_title,
        
        -- Phone checks
        CASE WHEN phone IS NULL OR TRIM(phone) = '' OR LOWER(TRIM(phone)) IN ('n/a', 'none', 'null', '0', 'unknown') THEN 1 ELSE 0 END AS is_missing_phone,
        
        -- Company ID checks
        CASE WHEN company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '' OR LOWER(TRIM(CAST(company_id AS VARCHAR))) IN ('unknown', 'need to fill data', 'n/a', 'none', 'null', '0') THEN 1 ELSE 0 END AS is_unmapped_company
    FROM read_parquet('{path}')
)
SELECT
    COUNT(*) as total,
    SUM(is_missing_email) as missing_emails,
    SUM(is_malformed_email) as malformed_emails,
    SUM(is_missing_name) as missing_names,
    SUM(is_initial_pattern_name) as initial_pattern_names,
    SUM(is_placeholder_name) as placeholder_names,
    SUM(is_missing_city) as missing_cities,
    SUM(is_city_equals_state_name) as city_is_state_names,
    SUM(is_city_has_comma) as city_with_commas,
    SUM(is_generic_or_missing_title) as generic_or_missing_titles,
    SUM(is_missing_phone) as missing_phones,
    SUM(is_unmapped_company) as unmapped_companies
FROM analyzed
"""

res = con.execute(audit_sql).fetchdf()
print(res.to_string())

# Save as JSON for planning
res_dict = res.to_dict(orient='records')[0]
with open(r"C:\TalentOpsAI\DEEP_ANOMALY_AUDIT.json", "w") as f:
    json.dump(res_dict, f, indent=2)
