import os
from sqlalchemy import text
from app.database import engine, Base
from app.models.models import *

def migrate():
    with engine.begin() as conn:
        print("Adding data_source and trust_score to companies...")
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN data_source VARCHAR(100) DEFAULT 'manual'"))
            conn.execute(text("ALTER TABLE companies ADD COLUMN trust_score INTEGER DEFAULT 100"))
        except Exception as e:
            print("Company columns might already exist:", e)

        print("Adding data_source and trust_score to recruiters...")
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN data_source VARCHAR(100) DEFAULT 'manual'"))
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN trust_score INTEGER DEFAULT 100"))
        except Exception as e:
            print("Recruiter columns might already exist:", e)

    print("Creating new Medallion tables (raw_uploads, staging_recruiters, staging_companies)...")
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
