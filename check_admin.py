from backend.app.database import SessionLocal
from backend.app.models.auth_models import User, Role
import json

db = SessionLocal()
admin = db.query(User).filter(User.email == 'abhishekjadon824@gmail.com').first()
if admin:
    role = db.query(Role).filter(Role.id == admin.role_id).first()
    print("Found admin:")
    print(f"ID: {admin.id}")
    print(f"Email: {admin.email}")
    print(f"Auth Provider: {admin.auth_provider}")
    print(f"Status: {admin.status}")
    print(f"Role: {role.name if role else 'None'}")
    print(f"Has Password Hash: {bool(admin.password_hash)}")
    print(f"Provider ID: {admin.provider_id}")
else:
    print("Admin account not found in database!")
db.close()
