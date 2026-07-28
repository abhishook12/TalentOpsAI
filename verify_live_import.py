import sqlalchemy
from sqlalchemy import text

DATABASE_URL = "postgresql+psycopg://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Starting strict 3-times verification protocol on the LIVE database...")

engine = sqlalchemy.create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("\n--- CHECK 1: Verifying total live database size ---")
        total_count = conn.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
        print(f"Total Recruiters in LIVE DB: {total_count}")
        
        print("\n--- CHECK 2: Verifying exactly how many records were inserted by the Arjun script ---")
        arjun_count = conn.execute(text("SELECT COUNT(*) FROM recruiters WHERE data_source = 'arjun_massive_import'")).scalar()
        print(f"Total Recruiters marked 'arjun_massive_import': {arjun_count}")

        print("\n--- CHECK 3: Verifying live data integrity by fetching a random sample of 3 new records ---")
        sample_records = conn.execute(text("SELECT recruiter_name, email FROM recruiters WHERE data_source = 'arjun_massive_import' LIMIT 3")).fetchall()
        for idx, row in enumerate(sample_records, 1):
            print(f"Sample {idx}: Name='{row[0]}', Email='{row[1]}'")
            
except Exception as e:
    print(f"Verification failed: {e}")
