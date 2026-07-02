import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
row = db.execute(text("SELECT COUNT(*) FILTER (WHERE state IS NOT NULL AND state != ''), COUNT(*) FILTER (WHERE state IS NULL OR state = '') FROM recruiters WHERE is_active = true")).fetchone()
print(f"\n==========================================")
print(f"REAL-TIME LOCAL UI TELEMETRY VERIFICATION:")
print(f"Known State Recruiters:   {row[0]:,}")
print(f"Unknown State Recruiters: {row[1]:,}")
print(f"==========================================")
db.close()
