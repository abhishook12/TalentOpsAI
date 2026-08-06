import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import func

def count_recruiters():
    db = SessionLocal()
    total = db.query(func.count(Recruiter.recruiter_id)).scalar()
    print(f"Total recruiters in DB: {total}")

if __name__ == "__main__":
    count_recruiters()
