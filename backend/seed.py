import os
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models.models import Recruiter
import json

def seed():
    db = SessionLocal()

    r1 = Recruiter(
        recruiter_name="Staging Agent Alpha",
        email="alpha1.staging@test.com",
        email2="alpha2.staging@test.com",
        email3="alpha3.staging@test.com",
        email4="alpha4.staging@test.com",
        phone="101-101-1010",
        phone2="202-202-2020",
        phone3="303-303-3030",
        phone4="404-404-4040",
        metadata_json=json.dumps({"email5": "alpha5.staging@test.com", "phone5": "505-505-5050"}),
        location="New York, NY",
        state="NY",
        specialization="Software Engineering",
        title="Technical Sourcer",
        data_source="manual_seed"
    )

    r2 = Recruiter(
        recruiter_name="Staging Agent Beta",
        email="beta1.staging@test.com",
        email2="beta2.staging@test.com",
        email3="beta3.staging@test.com",
        email4="beta4.staging@test.com",
        phone="606-606-6060",
        phone2="707-707-7070",
        phone3="808-808-8080",
        phone4="909-909-9090",
        metadata_json=json.dumps({"email5": "beta5.staging@test.com", "phone5": "000-000-0000"}),
        location="San Francisco, CA",
        state="CA",
        specialization="Product Management",
        title="Senior Recruiter",
        data_source="manual_seed"
    )

    db.add(r1)
    db.add(r2)
    try:
        db.commit()
        print("Successfully seeded Staging Agent Alpha and Staging Agent Beta!")
    except Exception as e:
        db.rollback()
        print("Error:", e)

if __name__ == "__main__":
    seed()
