import sys
import json
import uuid
from datetime import datetime
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.models import Recruiter
from app.routes.extension import (
    ingest_extension_batch,
    BatchRequest,
    ExtensionContact,
)
from starlette.requests import Request as StarletteRequest

db = SessionLocal()

print("=" * 70)
print("  TALENTOPS SCOUT — DEEP PROFILE ENRICHMENT VISUAL PROOF")
print("=" * 70)

admin_user = db.query(User).filter(User.id == 56).first()
device_id = f"ext-proof-{uuid.uuid4().hex[:8]}"

# Ensure clean slate for test
test_url = "https://www.linkedin.com/in/test-progressive-enrichment"
db.query(Recruiter).filter(Recruiter.linkedin == test_url).delete()
db.commit()

# --- STEP 1: INITIAL DISCOVERY (Basic Search Page Data) ---
disc_id_1 = f"DISC-PROOF-{uuid.uuid4().hex[:6].upper()}"
cap_id_1 = f"VC-PROOF-{uuid.uuid4().hex[:4].upper()}"

contact_1 = ExtensionContact(
    discovery_id=disc_id_1,
    capture_id=cap_id_1,
    recruiter_name="Kelsei Martinez",
    title="VP of Staffing",
    company_name="Premier Staffing Solution LLC",
    linkedin_url=test_url,
    location="Chicago, IL",
    source="visual_dom_fusion",
    source_url="https://www.linkedin.com/search/results/people/?keywords=staffing",
    confidence=95,
)

req_1 = BatchRequest(contacts=[contact_1], device_id=device_id)
scope = {"type": "http", "method": "POST", "path": "/recruiters/extension/batch", "headers": []}
mock_req = StarletteRequest(scope)

print("\n[STEP 1] SUBMITTING BASIC SEARCH CARD DISCOVERY (Initial Sighting)")
res_1 = ingest_extension_batch(req_1, mock_req, db, admin_user, device_id, "3.0.0")
print(f"  • API Response: {res_1}")

rec_1 = db.query(Recruiter).filter(Recruiter.linkedin == test_url).first()
import json
meta_1 = json.loads(rec_1.metadata_json) if rec_1.metadata_json else {}
print(f"  • Database State (After Step 1):")
print(f"    - Name: {rec_1.recruiter_name}")
print(f"    - Title: {rec_1.title}")
print(f"    - Education: {meta_1.get('education')}")
print(f"    - Skills: {meta_1.get('skills')}")
print(f"    - Certifications: {meta_1.get('certifications')}")


# --- STEP 2: FULL PROFILE ENRICHMENT (User opens candidate profile) ---
disc_id_2 = f"DISC-PROOF-{uuid.uuid4().hex[:6].upper()}"
cap_id_2 = f"VC-PROOF-{uuid.uuid4().hex[:4].upper()}"

contact_2 = ExtensionContact(
    discovery_id=disc_id_2,
    capture_id=cap_id_2,
    recruiter_name="Kelsei Martinez",
    title="VP of Staffing",
    company_name="Premier Staffing Solution LLC",
    linkedin_url=test_url,
    location="Chicago, IL",
    
    # NEW DEEP DATA:
    education="East Carolina University",
    skills=["Executive Search", "Client Relations", "Technical Recruiting"],
    certifications=[{"title": "Certified Recruiting Professional (CRP)", "issuer": "AIRS"}],
    experience_history=[{"title": "VP of Staffing", "company": "Premier Staffing Solution LLC", "is_current": True}],
    
    source="visual_dom_fusion",
    source_url=test_url,
    confidence=99,
)

req_2 = BatchRequest(contacts=[contact_2], device_id=device_id)
print("\n[STEP 2] SUBMITTING FULL PROFILE ENRICHMENT (User navigated to profile)")
res_2 = ingest_extension_batch(req_2, mock_req, db, admin_user, device_id, "3.0.0")
print(f"  • API Response: {res_2}")

db.commit()
rec_2 = db.query(Recruiter).filter(Recruiter.linkedin == test_url).first()
meta_2 = json.loads(rec_2.metadata_json) if rec_2.metadata_json else {}
print(f"  • Database State (After Step 2 - Deep Enrichment):")
print(f"    - Name: {rec_2.recruiter_name}")
print(f"    - Title: {rec_2.title}")
print(f"    - Education: {meta_2.get('education')}")
print(f"    - Skills: {meta_2.get('skills')}")
print(f"    - Certifications: {meta_2.get('certifications')}")
print(f"    - Experience: {meta_2.get('experience_history')}")

print("\n[FINAL CONCLUSION]")
if meta_2.get('education') == "East Carolina University" and "Executive Search" in str(meta_2.get('skills', [])):
    print(">>> SUCCESS! The main PostgreSQL database accurately synced the deep profile fields!")
else:
    print(">>> FAILED. The deep profile fields were not persisted.")

db.query(Recruiter).filter(Recruiter.linkedin == test_url).delete()
db.commit()
