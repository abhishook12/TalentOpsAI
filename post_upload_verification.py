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
    
    print(f"POST-UPLOAD COUNTS:")
    print(f"Total recruiters: {recruiters}")
    print(f"Total companies: {companies}")
    print(f"Total states: {states}")
    print(f"Total import jobs: {jobs}")
    
    # Check the latest job details
    last_job = conn.execute(text("SELECT * FROM smart_import_jobs ORDER BY started_at DESC LIMIT 1")).fetchone()
    if last_job:
        print("\n--- Latest Import Job Details ---")
        job_dict = dict(last_job._mapping)
        for k, v in job_dict.items():
            if k not in ['column_mapping']:
                print(f"{k}: {v}")
