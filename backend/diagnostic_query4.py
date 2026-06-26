import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    outcomes = db.execute(text('SELECT overall_outcome, count(*) FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' GROUP BY overall_outcome')).fetchall()
    print(outcomes)
    reasons = db.execute(text('SELECT rejection_reason, count(*) FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND rejection_reason IS NOT NULL GROUP BY rejection_reason ORDER BY count DESC LIMIT 10')).fetchall()
    print(reasons)
    fails = db.execute(text('SELECT failure_category, count(*) FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND failure_category IS NOT NULL GROUP BY failure_category ORDER BY count DESC LIMIT 10')).fetchall()
    print(fails)
finally:
    db.close()
