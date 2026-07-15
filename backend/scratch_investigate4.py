import pandas as pd
from app.database import engine
from sqlalchemy import text
import json

query = """
SELECT recruiter_id, recruiter_name, email, company_id
FROM recruiters 
WHERE recruiter_name ILIKE '%Robert Mihalyi%' OR email ILIKE '%aterry@%';
"""
print("Checking Robert Mihalyi and aterry@teksystems.com:")
with engine.connect() as conn:
    print(pd.read_sql_query(text(query), conn))

