import sys
from sqlalchemy import func
from app.database import SessionLocal
from app.models.models import Recruiter, EnrichmentAudit, Company

session = SessionLocal()

total_recruiters = session.query(func.count(Recruiter.recruiter_id)).scalar()
null_email = session.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.email == None).scalar()

print('Total recruiters:', total_recruiters)
print('Recruiters without email:', null_email)

# Sample recruiters without email (limit 5)
print('\nSample recruiters without email:')
for r in session.query(Recruiter).filter(Recruiter.email == None).limit(5).all():
    print(f'ID:{r.recruiter_id} Name:"{r.recruiter_name}"')

# Audit action counts
print('\nEnrichmentAudit action counts:')
for action, count in session.query(EnrichmentAudit.action, func.count()).group_by(EnrichmentAudit.action).all():
    print(f'{action}: {count}')

session.close()
