import sys
import os

sys.path.append("C:/TalentOpsAI/backend")

from app.services.auth_service import get_password_hash, verify_password
from app.database import SessionLocal
from app.models.auth_models import User
from sqlalchemy import text

db = SessionLocal()

email = "abhishekjadon706@gmail.com"
password = "Kx7!mQp2"

user = db.query(User).filter(User.email == email).first()

if user:
    print(f"Old hash: {user.password_hash}")
    new_hash = get_password_hash(password)
    user.password_hash = new_hash
    user.status = "Active"
    db.commit()
    print(f"Updated hash to: {new_hash}")
    
    # Verify it immediately
    is_valid = verify_password(password, new_hash)
    print(f"Verification result: {is_valid}")
    
    # Check rate limit or history
    recent_fails = db.execute(text(f"SELECT COUNT(*) FROM login_history WHERE email='{email}' AND status='Failed'")).scalar()
    print(f"Recent fails: {recent_fails}")
    
    # Clear fails to prevent rate limiting
    db.execute(text(f"DELETE FROM login_history WHERE email='{email}'"))
    db.commit()
    print("Cleared login history for this email.")
else:
    print("User not found via ORM!")
