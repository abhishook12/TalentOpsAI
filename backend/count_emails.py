import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import RecruiterEmail
from sqlalchemy import func

def count_emails():
    db = SessionLocal()
    total = db.query(func.count(RecruiterEmail.id)).scalar()
    print(f"Total emails in DB: {total}")

if __name__ == "__main__":
    count_emails()
