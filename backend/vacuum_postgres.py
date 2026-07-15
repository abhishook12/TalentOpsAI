import psycopg
import os
from sqlalchemy import create_engine, text

# Get postgres connection string
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")

print("Running VACUUM FULL on recruiters...")
with engine.connect() as conn:
    conn.execute(text("VACUUM FULL recruiters;"))
    print("Done recruiters.")
    
    print("Running VACUUM FULL on companies...")
    conn.execute(text("VACUUM FULL companies;"))
    print("Done companies.")
    
    print("Running VACUUM FULL on enrichment_results...")
    conn.execute(text("VACUUM FULL enrichment_results;"))
    print("Done enrichment_results.")
    
    size_query = text("SELECT pg_database_size(current_database()) / 1048576.0")
    print(f"New Total DB Size: {conn.execute(size_query).scalar()} MB")
