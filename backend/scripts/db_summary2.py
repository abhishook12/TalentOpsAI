import os, sys
# Ensure backend directory is in PYTHONPATH
backend_path = os.path.abspath(os.path.dirname(__file__) + '/../')
sys.path.append(backend_path)

from app.database import SessionLocal
from app.models.models import Recruiter, EnrichmentAudit
from sqlalchemy import func

session = SessionLocal()

total = session.query(func.count(Recruiter.recruiter_id)).scalar()
null_email = session.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.email == None).scalar()
print('Total recruiters:', total)
print('Recruiters without email:', null_email)

print('\nSample recruiters without email (up to 10):')
for r in session.query(Recruiter).filter(Recruiter.email == None).limit(10).all():
    print(f'ID:{r.recruiter_id} Name:"{r.recruiter_name}"')

print('\nEnrichmentAudit action counts:')
for action, count in session.query(EnrichmentAudit.action, func.count()).group_by(EnrichmentAudit.action).all():
    print(f'{action}: {count}')

print('\nAudit records for recruiter ID 202580 (Freddy Engel):')
for a in session.query(EnrichmentAudit).filter(EnrichmentAudit.recruiter_id == 202580).all():
    print(f'Action:{a.action} Reason:{a.reason} Final:{a.final_value}')

session.close()
