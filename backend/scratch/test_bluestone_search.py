import requests
import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

db = SessionLocal()
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
db.close()

headers = {"Authorization": f"Bearer {token}", "X-Session-ID": str(session.id)}
BACKEND_URL = "http://127.0.0.1:8000"

print("--- Testing /analytics/companies-search?q=blueStone ---")
try:
    r = requests.get(f"{BACKEND_URL}/analytics/companies-search?q=blueStone&limit=10&min_recruiters=1", headers=headers, timeout=10)
    print("Status:", r.status_code)
    print("Response:", r.text[:500])
except Exception as e:
    print("Request failed:", e)

print("\n--- Inspecting DuckDB for 'bluestone' ---")
import duckdb
con = duckdb.connect()
print(con.execute("""
    SELECT company_name, email, company_id, COUNT(*) as cnt
    FROM read_parquet('data/recruiters_full.parquet')
    WHERE company_name ILIKE '%bluestone%' OR email ILIKE '%bluestone%' OR CAST(company_id AS VARCHAR) ILIKE '%bluestone%'
    GROUP BY company_name, email, company_id
    LIMIT 10
""").df())
