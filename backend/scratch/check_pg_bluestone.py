import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Company

db = SessionLocal()
comps = db.query(Company).filter(Company.company_name.ilike("%bluestone%")).all()
print(f"Found {len(comps)} Bluestone companies in PostgreSQL:")
for c in comps:
    print(f"  - ID: {c.company_id} | Name: {c.company_name} | Pattern: {c.email_pattern} | Web: {c.website}")

db.close()
