import sys
sys.path.append(r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Role
from app.services.auth_service import get_password_hash

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "admin@talentops.com").first()
    
    if not user:
        print("Admin user not found. Creating...")
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        role_id = admin_role.id if admin_role else None
        
        user = User(
            email="admin@talentops.com",
            first_name="Admin",
            last_name="User",
            password_hash=get_password_hash("1012"),
            role_id=role_id,
            status="Active"
        )
        db.add(user)
        db.commit()
        print("Admin user created with password '1012'.")
    else:
        print(f"User found: {user.email}")
        user.password_hash = get_password_hash("1012")
        db.commit()
        print("Password reset to '1012' successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
