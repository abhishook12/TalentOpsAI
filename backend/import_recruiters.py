import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db, engine
from app.models.models import Recruiter, Base
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)

with open(os.path.join(os.path.dirname(__file__), "app", "recruiters.json"), "r") as f:
    recruiters = json.load(f)

db: Session = next(get_db())

print(f"Importing {len(recruiters)} recruiters...")

added = 0
skipped = 0

for r in recruiters:
    email = r.get("email", "").strip()[:150]
    name = r.get("recruiter_name", "").strip()[:150]
    phone = r.get("phone", "").strip()[:50]
    specialization = r.get("location", "").strip()[:150]

    if not name:
        skipped += 1
        continue

    if email:
        existing = db.query(Recruiter).filter(Recruiter.email == email).first()
        if existing:
            skipped += 1
            continue

    rec = Recruiter(
        recruiter_name=name,
        email=email if email else f"unknown_{added}@noemail.com",
        phone=phone,
        specialization=specialization,
        is_active=True,
    )
    db.add(rec)
    added += 1

    if added % 500 == 0:
        db.commit()
        print(f"  {added} added so far...")

db.commit()
print(f"\nDone! Added: {added}, Skipped: {skipped}")
