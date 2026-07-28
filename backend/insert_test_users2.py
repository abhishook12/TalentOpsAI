from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import get_password_hash

db = SessionLocal()

def upsert_user(email, password, role):
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(email=email)
        db.add(u)
    u.password_hash = get_password_hash(password)
    u.role = role
    u.first_name = "Test"
    u.last_name = "User"
    db.commit()
    print(f"Upserted {email}")

upsert_user('test_user@example.com', 'User123!@#', 'standard')
upsert_user('admin@talentops.ai', 'Admin123!@#', 'admin')
