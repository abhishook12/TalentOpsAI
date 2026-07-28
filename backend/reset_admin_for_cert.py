"""
Reset admin password to a known value for certification testing.
"""
import bcrypt
from app.database import SessionLocal
from app.models.auth_models import User

NEW_PASSWORD = "Admin@TalentOps2026"

db = SessionLocal()
u = db.query(User).filter(User.email == 'admin@talentops.com').first()
if u:
    hashed = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    u.password_hash = hashed
    db.commit()
    print(f"[OK] Admin password reset to: {NEW_PASSWORD}")
    print(f"   New hash prefix: {hashed[:25]}...")
else:
    print("[FAIL] Admin user not found!")
db.close()
