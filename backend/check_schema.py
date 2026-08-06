import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Recruiter, RecruiterEmail

def check_schema():
    db = SessionLocal()
    r = db.query(Recruiter).first()
    print("Recruiter keys:", r.__dict__.keys())
    
    re = db.query(RecruiterEmail).first()
    if re:
        print("RecruiterEmail keys:", re.__dict__.keys())

if __name__ == "__main__":
    check_schema()
