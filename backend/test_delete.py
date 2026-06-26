from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import text
db = SessionLocal()
try:
    r = db.query(Recruiter).filter_by(email='fake_person_test@example.com').first()
    if r:
        db.delete(r)
        db.commit()
        print('Deleted successfully')
    else:
        print('Not found')
except Exception as e:
    print('Error:', e)
finally:
    db.close()
