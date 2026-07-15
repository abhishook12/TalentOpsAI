import pandas as pd
from app.database import engine
from sqlalchemy import text

# 1. Check how many recruiters have the same name as their company
query1 = """
SELECT count(*) as count
FROM recruiters r 
JOIN companies c ON r.company_id = c.company_id 
WHERE lower(trim(r.recruiter_name)) = lower(trim(c.company_name));
"""
print("Count of recruiter names exactly matching company name:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query1), conn))

# 2. Check if the name looks like an email prefix
query2 = """
SELECT count(*) as count
FROM recruiters 
WHERE recruiter_name LIKE '%@%';
"""
print("\nCount of recruiter names containing @:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query2), conn))

# 3. Check for TEKsystems explicitly
query3 = """
SELECT r.recruiter_name, r.email, r.location 
FROM recruiters r 
JOIN companies c ON r.company_id = c.company_id 
WHERE c.company_name ILIKE '%TEKsystems%' 
LIMIT 10;
"""
print("\nSample of TEKsystems recruiters:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query3), conn))

# 4. Check location distribution
query4 = """
SELECT count(*) as count, c.company_name, r.location, c.location as company_location
FROM recruiters r
JOIN companies c ON r.company_id = c.company_id
WHERE r.location = c.location
GROUP BY c.company_name, r.location, c.location
ORDER BY count DESC
LIMIT 5;
"""
print("\nCompanies with recruiters falling back to company location:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query4), conn))
