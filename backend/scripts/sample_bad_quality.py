import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import func
db = SessionLocal()

print('=== SAMPLE: Names <= 2 chars ===')
for r in db.query(Recruiter).filter(func.length(Recruiter.recruiter_name) <= 2).limit(15).all():
    print(f'  ID:{r.recruiter_id} | Name:"{r.recruiter_name}" | Email:{r.email}')

print()
print('=== SAMPLE: Name looks like email ===')
for r in db.query(Recruiter).filter(Recruiter.recruiter_name.contains('@')).limit(10).all():
    print(f'  ID:{r.recruiter_id} | Name:"{r.recruiter_name}" | Email:{r.email}')

print()
print('=== SAMPLE: Bad email status ===')
for r in db.query(Recruiter).filter(Recruiter.email_status.in_(['invalid', 'bounced', 'spam_trap'])).limit(10).all():
    print(f'  ID:{r.recruiter_id} | Name:"{r.recruiter_name}" | Email:{r.email} | Status:{r.email_status}')

print()
print('=== SAMPLE: Low completeness (<30) ===')
for r in db.query(Recruiter).filter(Recruiter.completeness_score < 30).limit(10).all():
    print(f'  ID:{r.recruiter_id} | Name:"{r.recruiter_name}" | Email:{r.email} | Phone:{r.phone} | Title:{r.title} | Score:{r.completeness_score}')

print()
print('=== SAMPLE: needs_review flagged ===')
for r in db.query(Recruiter).filter(Recruiter.needs_review == True).limit(10).all():
    print(f'  ID:{r.recruiter_id} | Name:"{r.recruiter_name}" | Email:{r.email} | Reason:{r.review_reason}')
