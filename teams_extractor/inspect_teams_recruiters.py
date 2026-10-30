import sys
sys.path.insert(0, r'C:\TalentOpsAI')
from backend.app.database import SessionLocal
from backend.app.models.models import Recruiter

db = SessionLocal()
try:
    recs = db.query(Recruiter).filter(Recruiter.data_source.ilike('%teams%')).limit(5).all()
    for r in recs:
        print(f"{r.recruiter_id}: {r.recruiter_name} | Co: {r.company_id} | Email: {r.email} | Phone: {r.phone} | Source: {r.data_source} | Created: {r.created_at}")
finally:
    db.close()
