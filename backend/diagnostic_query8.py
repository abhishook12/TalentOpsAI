import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    samples = db.execute(text('SELECT recruiter_id, original_value, final_value, source, confidence_score, created_at, enrichment_type FROM enrichment_audit WHERE run_id = \'full-enrichment-20260623-221909\' AND action = \'applied\' LIMIT 20')).fetchall()
    print(json.dumps([{'id': s[0], 'old': s[1], 'new': s[2], 'source': s[3], 'conf': s[4], 'time': str(s[5]), 'field': s[6]} for s in samples], indent=2))
finally:
    db.close()
