import sys
import os

# Add backend directory to path
sys.path.append(r"C:\TalentOpsAI\backend")

from app.database import SessionLocal
from app.models.auth_models import User, Role
import bcrypt

db = SessionLocal()

# Ensure role exists
user_role = db.query(Role).filter_by(name="user").first()
if not user_role:
    user_role = Role(name="user", description="Standard User")
    db.add(user_role)
    db.commit()
    db.refresh(user_role)

user_email = "test2@talentops.com"
existing_user = db.query(User).filter_by(email=user_email).first()

password = "User@TalentOps2026"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

if existing_user:
    existing_user.password_hash = hashed
    existing_user.status = "Active"
else:
    new_user = User(
        email=user_email,
        password_hash=hashed,
        first_name="Test",
        last_name="User2",
        role_id=user_role.id,
        status="Active"
    )
    db.add(new_user)

db.commit()
print("Provisioned test2@talentops.com")
