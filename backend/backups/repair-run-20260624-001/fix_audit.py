import sys
sys.path.append('C:/TalentOpsAI/backend')
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("""
    UPDATE enrichment_audit 
    SET action='rejected_duplicate_email', 
        reason='Email already assigned to recruiter ID 16488, Fred Engel' 
    WHERE recruiter_id=202580 AND action='Applied'
"""))
db.commit()
print("False audit fixed.")
