from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import text
db = SessionLocal()
try:
    r = Recruiter(recruiter_name='Fake Person For Test', email='fake_person_test@example.com', data_source='manual')
    db.add(r)
    db.commit()
    print('Inserted successfully')
except Exception as e:
    print('Error:', e)
finally:
    db.close()
