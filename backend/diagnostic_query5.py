import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    samples = db.execute(text('SELECT recruiter_id, old_values_json, applied_values_json, confidence_json FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND overall_outcome = \'APPLIED\' LIMIT 2')).fetchall()
    print(samples)
finally:
    db.close()
