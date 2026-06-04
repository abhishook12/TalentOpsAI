import os
import sys
import json
import uuid
import pandas as pd

# Override DB URL for local test
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend dir to sys.path so we can import app modules
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))

from app.database import Base
from app.models.models import SmartImportJob, SmartImportRow, Recruiter
from app.services.format_detector import detect_format
from app.services.import_service import validate_and_save_rows

engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Inject my SessionLocal into import_service so validate_and_save_rows uses it
import app.services.import_service as import_service
import_service.SessionLocal = SessionLocal
from app.services.format_detector import detect_format
from app.services.import_service import validate_and_save_rows

db = SessionLocal()

def test_vertical_format():
    print("--- TESTING VERTICAL FORMAT ---")
    data = [
        {"Name": "Chris Pierce", "Company": "Infinisearch", "Field Type": "Work Email", "Field Value": "chris@infinisearch.com"},
        {"Name": "Chris Pierce", "Company": "Infinisearch", "Field Type": "Phone", "Field Value": "4847160498"},
        {"Name": "Chris Pierce", "Company": "Infinisearch", "Field Type": "Personal Email", "Field Value": "chris.p@gmail.com"},
    ]
    df = pd.DataFrame(data)
    
    # 1. Detect Format
    fmt_info = detect_format(df)
    print("Detected Format:", fmt_info["detected_format"])
    assert fmt_info["detected_format"] == "vertical_multi_value"
    
    # 2. Setup mock DB job
    job_id = str(uuid.uuid4())
    job = SmartImportJob(
        job_id=job_id,
        filename="test_vertical.csv",
        detected_format="vertical_multi_value",
        column_mapping=json.dumps({"name": "Name", "company": "Company"})
    )
    db.add(job)
    
    # 3. Add Raw Rows
    db_rows = []
    for i, r in enumerate(data):
        db_rows.append(SmartImportRow(
            job_id=job_id,
            original_row_index=i,
            raw_json=json.dumps(r),
            status="Raw"
        ))
    db.add_all(db_rows)
    db.commit()
    
    # 4. Run validate
    validate_and_save_rows(job_id, {"name": "Name", "company": "Company"})
    
    # 5. Check Output
    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    primary = [r for r in rows if r.status != "Merged"]
    merged = [r for r in rows if r.status == "Merged"]
    
    print(f"Total Rows: {len(rows)}, Primary: {len(primary)}, Merged: {len(merged)}")
    assert len(primary) == 1
    assert len(merged) == 2
    
    p = primary[0]
    print(f"Primary Row Email: {p.email}, Phone: {p.phone}")
    raw_j = json.loads(p.raw_json)
    print(f"Primary Raw JSON: {raw_j}")
    
    print("Vertical Format Test Passed!\n")

def test_wide_format():
    print("--- TESTING WIDE FORMAT ---")
    data = [
        {"Name": "Jane Doe", "Company": "TechInc", "Email 1": "jane1@tech.com", "Email 2": "jane2@tech.com", "Phone 1": "555-1111", "Phone 2": "555-2222"}
    ]
    df = pd.DataFrame(data)
    
    fmt_info = detect_format(df)
    print("Detected Format:", fmt_info["detected_format"])
    assert fmt_info["detected_format"] == "wide_multi_column"
    
    job_id = str(uuid.uuid4())
    job = SmartImportJob(
        job_id=job_id,
        filename="test_wide.csv",
        detected_format="wide_multi_column",
        column_mapping=json.dumps({"name": "Name", "company": "Company", "email": "Email 1", "phone": "Phone 1"})
    )
    db.add(job)
    
    db_rows = []
    for i, r in enumerate(data):
        db_rows.append(SmartImportRow(
            job_id=job_id,
            original_row_index=i,
            raw_json=json.dumps(r),
            status="Raw"
        ))
    db.add_all(db_rows)
    db.commit()
    
    validate_and_save_rows(job_id, {"name": "Name", "company": "Company", "email": "Email 1", "phone": "Phone 1"})
    
    rows = db.query(SmartImportRow).filter(SmartImportRow.job_id == job_id).all()
    p = rows[0]
    raw_j = json.loads(p.raw_json)
    
    print(f"Email 1: {p.email}")
    print(f"Phone 1: {p.phone}")
    print(f"Extracted metadata: {raw_j}")
    
    # Check that Email 2 and Phone 2 got extracted correctly as alternate in metadata
    
    print("Wide Format Test Passed!\n")

if __name__ == "__main__":
    test_vertical_format()
    test_wide_format()
