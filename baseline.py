import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    recruiters = conn.execute(text("SELECT count(*) FROM recruiters")).scalar()
    companies = conn.execute(text("SELECT count(*) FROM companies")).scalar()
    states = conn.execute(text("SELECT count(DISTINCT state) FROM recruiters WHERE state IS NOT NULL")).scalar()
    jobs = conn.execute(text("SELECT count(*) FROM smart_import_jobs")).scalar()
    
    print(f"BASELINE COUNTS:")
    print(f"Total recruiters: {recruiters}")
    print(f"Total companies: {companies}")
    print(f"Total states: {states}")
    print(f"Total import jobs: {jobs}")
