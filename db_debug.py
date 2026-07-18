from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use the production DB URL
DB_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

with SessionLocal() as db:
    # Query campaigns
    from sqlalchemy import text
    camps = db.execute(text("SELECT campaign_id, name, status FROM campaigns ORDER BY campaign_id DESC LIMIT 5")).fetchall()
    print("Recent Campaigns:", camps)
    
    recs = db.execute(text("SELECT campaign_recruiter_id, campaign_id, status FROM campaign_recruiters ORDER BY campaign_recruiter_id DESC LIMIT 5")).fetchall()
    print("Recent Recipients:", recs)
    
    logs = db.execute(text("SELECT log_id, campaign_id, status, error_message, sent_via FROM email_logs ORDER BY log_id DESC LIMIT 5")).fetchall()
    print("Recent EmailLogs:", logs)
