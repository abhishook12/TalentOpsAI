import requests
import json
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
r = requests.get("http://127.0.0.1:8000/analytics/companies-search?limit=10&min_recruiters=1", headers=headers)
print("Status:", r.status_code)
for item in r.json()[:5]:
    print(item)
