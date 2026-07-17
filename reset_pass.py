import sys
sys.path.append("C:/TalentOpsAI/backend")

from app.services.auth_service import get_password_hash
from app.database import SessionLocal
from app.models.auth_models import User
from sqlalchemy import text

db = SessionLocal()

email = "abhishekjadon824@gmail.com"
password = "StrongPassword123!"

user = db.query(User).filter(User.email == email).first()
if user:
    user.password_hash = get_password_hash(password)
    user.status = "Active"
    db.commit()
    print("Password updated successfully.")
else:
    print("User not found!")
