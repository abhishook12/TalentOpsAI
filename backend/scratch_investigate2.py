import pandas as pd
from app.database import engine
from sqlalchemy import text

# 1. Top recruiter names for TEKsystems
query1 = """
SELECT recruiter_name, count(*) as count
FROM recruiters
WHERE company_id = (SELECT company_id FROM companies WHERE company_name ILIKE 'TEKsystems' LIMIT 1)
GROUP BY recruiter_name
ORDER BY count DESC
LIMIT 10;
"""
print("Top recruiter names for TEKsystems:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query1), conn))

# 2. Are there emails mismatched with names?
query2 = """
SELECT recruiter_name, email
FROM recruiters
WHERE company_id = (SELECT company_id FROM companies WHERE company_name ILIKE 'TEKsystems' LIMIT 1)
AND recruiter_name ILIKE 'Tek Systems'
LIMIT 10;
"""
print("\nEmails for recruiters named 'Tek Systems':")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query2), conn))

# 3. Look for 'Bcubed Engineering Corp.'
query3 = """
SELECT * FROM recruiters WHERE recruiter_name = 'Bcubed Engineering Corp.';
"""
print("\nBcubed Engineering Corp. record:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query3), conn))
