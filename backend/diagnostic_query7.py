import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    samples = db.execute(text('SELECT recruiter_id, previous_value, new_value, confidence_score, updated_at FROM enrichment_audit WHERE enrichment_type = \'email\' ORDER BY updated_at DESC LIMIT 20')).fetchall()
    print([{'id': s[0], 'old': s[1], 'new': s[2], 'conf': s[3], 'time': str(s[4])} for s in samples])
finally:
    db.close()
