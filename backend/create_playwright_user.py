from app.database import SessionLocal
from app.models.auth_models import User, Role
from app.services.auth_service import get_password_hash

db = SessionLocal()
email = "playwright@talentops.ai"
user = db.query(User).filter(User.email == email).first()
role_obj = db.query(Role).filter(Role.name == "superadmin").first()

if not user:
    user = User(
        email=email,
        password_hash=get_password_hash("password123"),
        role=role_obj,
        first_name="Play",
        last_name="Wright"
    )
    db.add(user)
    db.commit()
    print("Created playwright user.")
else:
    user.password_hash = get_password_hash("password123")
    user.role = role_obj
    db.commit()
    print("Updated playwright user.")
