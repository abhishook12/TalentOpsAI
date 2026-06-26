import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    records = db.execute(text('SELECT id, recruiter_id, original_value, final_value, confidence_score, created_at FROM enrichment_audit WHERE run_id = \'full-enrichment-20260623-221909\' AND action = \'applied\'')).fetchall()
    data = [{'audit_id': r[0], 'recruiter_id': r[1], 'original': r[2], 'final': r[3], 'conf': r[4]} for r in records]
    with open('96_records.json', 'w') as f:
        json.dump(data, f)
finally:
    db.close()
