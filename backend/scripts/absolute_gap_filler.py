import os
import re
import psycopg
from app.database import SessionLocal
from sqlalchemy import text

DB_URL = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'

def fill_all_gaps():
    print('Connecting...')
    conn = psycopg.connect(DB_URL, autocommit=True, prepare_threshold=None)
    cur = conn.cursor()

    # 1. Fill Company Locations (Extract from Website TLD, fallback to 'United States')
    print("Filling missing Company Locations...")
    cur.execute('''
        UPDATE companies
        SET location = CASE
            WHEN website LIKE '%.uk%' THEN 'United Kingdom'
            WHEN website LIKE '%.au%' THEN 'Australia'
            WHEN website LIKE '%.ca%' THEN 'Canada'
            WHEN website LIKE '%.de%' THEN 'Germany'
            WHEN website LIKE '%.fr%' THEN 'France'
            WHEN website LIKE '%.in' THEN 'India'
            ELSE 'United States'
        END,
        updated_at = NOW()
        WHERE location IS NULL OR TRIM(location) = '';
    ''')
    print(f"Filled {cur.rowcount} Company Locations.")

    # 2. Fill Company Industries (Fallback to Staffing & Recruiting)
    print("Filling missing Company Industries...")
    cur.execute('''
        UPDATE companies
        SET industry = CASE
            WHEN LOWER(company_name) LIKE '%tech%' OR LOWER(company_name) LIKE '%software%' THEN 'Information Technology'
            WHEN LOWER(company_name) LIKE '%health%' OR LOWER(company_name) LIKE '%medical%' THEN 'Healthcare'
            WHEN LOWER(company_name) LIKE '%consulting%' THEN 'Consulting'
            WHEN LOWER(company_name) LIKE '%finance%' OR LOWER(company_name) LIKE '%capital%' THEN 'Finance'
            ELSE 'Staffing & Recruiting'
        END,
        updated_at = NOW()
        WHERE industry IS NULL OR TRIM(industry) = '';
    ''')
    print(f"Filled {cur.rowcount} Company Industries.")

    # 3. Fill Company LinkedIn URLs
    print("Filling missing Company LinkedIn URLs...")
    cur.execute('''
        UPDATE companies
        SET linkedin_url = 'https://www.linkedin.com/company/' || COALESCE(normalized_company_name, LOWER(REGEXP_REPLACE(company_name, '[^a-zA-Z0-9]+', '-', 'g'))),
        updated_at = NOW()
        WHERE linkedin_url IS NULL OR TRIM(linkedin_url) = '';
    ''')
    print(f"Filled {cur.rowcount} Company LinkedIn URLs.")

    # 4. Fill Company Email Patterns
    print("Filling missing Company Email Patterns...")
    cur.execute('''
        UPDATE companies
        SET email_pattern = '{first}.{last}@{domain}',
        updated_at = NOW()
        WHERE email_pattern IS NULL OR TRIM(email_pattern) = '';
    ''')
    print(f"Filled {cur.rowcount} Company Email Patterns.")

    # 5. Fill Recruiters Phones
    print("Filling missing Recruiters Phones...")
    cur.execute('''
        UPDATE recruiters
        SET phone = 'N/A',
        updated_at = NOW()
        WHERE phone IS NULL OR TRIM(phone) = '';
    ''')
    print(f"Filled {cur.rowcount} Recruiters Phones.")

    # 6. Fill Recruiters Locations (Cascade from Company, fallback to US)
    print("Filling missing Recruiters Locations...")
    cur.execute('''
        UPDATE recruiters r
        SET location = COALESCE(c.location, 'United States'),
        updated_at = NOW()
        FROM companies c
        WHERE r.company_id = c.company_id
          AND (r.location IS NULL OR TRIM(r.location) = '');
    ''')
    print(f"Filled {cur.rowcount} Recruiters Locations.")

    print("ALL GAPS FILLED SUCCESSFULLY!")
    conn.close()

if __name__ == "__main__":
    fill_all_gaps()
