import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend.app.database import SessionLocal
from backend.app.models.auth_models import User
from backend.app.services.auth_service import get_password_hash

with SessionLocal() as db:
    email = "admin.uat@talentops.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash("Admin123!"),
            role_id=1,
            organization_id=1,
            status="Active"
        )
        db.add(user)
        db.commit()
        print(f"Created {email}")
    else:
        user.password_hash = get_password_hash("Admin123!")
        db.commit()
        print(f"Updated password for {email}")
