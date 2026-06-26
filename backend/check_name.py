from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    name = db.execute(text('SELECT recruiter_name FROM recruiters WHERE recruiter_id = 623')).scalar()
    print(name)
finally:
    db.close()
