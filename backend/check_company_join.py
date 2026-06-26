#!/usr/bin/env python
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("""
    SELECT count(*), count(company_id) 
    FROM recruiters 
    WHERE state IS NULL OR state = '';
""")).fetchone()
print(f"Total unknown state rows: {res[0]} | Rows with company_id: {res[1]}")

sample = db.execute(text("""
    SELECT r.recruiter_name, r.location, c.company_name, c.location
    FROM recruiters r
    LEFT JOIN companies c ON r.company_id = c.company_id
    WHERE r.state IS NULL OR r.state = ''
    LIMIT 15;
""")).fetchall()
for s in sample:
    print(s)
db.close()
