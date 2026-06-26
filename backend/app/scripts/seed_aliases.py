import os
import psycopg
from dotenv import load_dotenv

load_dotenv("C:/TalentOpsAI/backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(DATABASE_URL, prepare_threshold=None)

with conn.cursor() as cur:
    cur.execute("SELECT company_id FROM companies WHERE company_name ILIKE '%INSPYR%'")
    inspyr = cur.fetchone()
    print('INSPYR:', inspyr)
    
    if not inspyr:
        cur.execute("INSERT INTO companies (company_name, normalized_company_name, website) VALUES ('INSPYR Solutions', 'inspyrsolutions', 'inspyrsolutions.com') RETURNING company_id")
        inspyr = cur.fetchone()
        print('Created INSPYR:', inspyr)

    cur.execute("INSERT INTO company_aliases (canonical_company_id, alias_name, alias_type) VALUES (%s, 'TekPartners', 'former_name')", (inspyr[0],))
    conn.commit()
    print("Alias added.")
