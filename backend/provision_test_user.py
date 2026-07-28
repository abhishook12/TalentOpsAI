import sys
import os

# Add backend directory to path
sys.path.append(r"C:\TalentOpsAI\backend")

from app.database import SessionLocal
from app.models.auth_models import User, Role
import bcrypt

db = SessionLocal()

try:
    # Ensure role exists
    user_role = db.query(Role).filter_by(name="user").first()
    if not user_role:
        user_role = Role(name="user", description="Standard User")
        db.add(user_role)
        db.commit()
        db.refresh(user_role)
    
    # Check if user exists
    user_email = "user@talentops.com"
    existing_user = db.query(User).filter_by(email=user_email).first()
    
    password = "User@TalentOps2026"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    if existing_user:
        existing_user.password_hash = hashed
        existing_user.role_id = user_role.id
        existing_user.status = "Active"
        print(f"[OK] Test user {user_email} already exists, password and role reset.")
    else:
        new_user = User(
            email=user_email,
            password_hash=hashed,
            first_name="Test",
            last_name="User",
            role_id=user_role.id,
            status="Active"
        )
        db.add(new_user)
        print(f"[OK] Test user {user_email} created successfully.")
        
    db.commit()
    
except Exception as e:
    print(f"[FAIL] Error provisioning test user: {e}")
finally:
    db.close()
