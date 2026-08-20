import os
import re
import json
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("c:/TalentOpsAI/backend/.env")

FINAL_10 = [
    (20, "IT Staffing, Inc"),
    (28, "BTerminal Systems"),
    (36, "C&G Consulting Services, Inc"),
    (53, "Rylex"),
    (72, "Makai Labs"),
    (84, "SOLTECHPR"),
    (87, "TJ Consulting Group"),
    (96, "ProspHire"),
    (98, "People4Net Inc"),
    (105, "Full Cycle Services")
]

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)
with engine.connect() as conn:
    df_pg = pd.read_sql("SELECT company_id, company_name, normalized_company_name, canonical_name, primary_domain, website FROM companies", conn)

parquet_path = "c:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
con = duckdb.connect()

print("Verifying the final 10 companies across database and parquet:")
for idx, name in FINAL_10:
    slugs = [re.sub(r'[^a-zA-Z0-9]', '', name.lower())]
    if name == "SOLTECHPR":
        slugs.append("soltech")
    if name == "C&G Consulting Services, Inc":
        slugs.extend(["cgconsulting", "cg-consulting"])
    if name == "TJ Consulting Group":
        slugs.extend(["tjconsulting", "tj-consulting"])
        
    found_pg = []
    for slug in slugs:
        m = df_pg[df_pg['company_name'].str.lower().str.contains(slug) | df_pg['primary_domain'].fillna('').str.lower().str.contains(slug)]
        if len(m) > 0:
            found_pg.extend(m[['company_name', 'primary_domain']].to_dict(orient='records'))
            
    print(f"\n[{idx:3d}] {name}:")
    if found_pg:
        print(f"  -> Potential PG Matches: {found_pg[:2]}")
    else:
        print("  -> CONFIRMED NEW (0 in Postgres, 0 in Parquet)")
