import sys
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.auth_models import User, Role
from app.services.auth_service import get_password_hash

def seed_admin():
    db = SessionLocal()
    try:
        # Ensure superadmin role exists
        role = db.query(Role).filter(Role.name == "superadmin").first()
        if not role:
            role = Role(name="superadmin", description="Full platform access")
            db.add(role)
            db.commit()
            db.refresh(role)

        # Ensure admin user exists
        admin_email = "admin@talentops.com"
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            user = User(
                email=admin_email,
                password_hash=get_password_hash("admin123456"),
                first_name="Admin",
                last_name="System",
                status="Active",
                role_id=role.id,
                auth_provider="local"
            )
            db.add(user)
            print(f"Created user {admin_email} with password 'admin123456'")
        else:
            user.password_hash = get_password_hash("admin123456")
            user.status = "Active"
            user.role_id = role.id
            print(f"Updated user {admin_email} with password 'admin123456' and status Active")
        db.commit()
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
