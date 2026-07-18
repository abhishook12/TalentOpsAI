from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time

DB_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print("Starting query...")
start = time.time()
with SessionLocal() as db:
    from sqlalchemy import text
    res = db.execute(text("SELECT log_id FROM email_logs WHERE status = 'sending' AND sent_via = 'outlook_bridge' AND outlook_accepted IS NULL LIMIT 10")).fetchall()
    print("Result:", res)
print("Finished in", time.time() - start)
