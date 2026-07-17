from backend.app.database import SessionLocal
from backend.app.models.auth_models import User, Role
import json

db = SessionLocal()
admin = db.query(User).filter(User.email == 'abhishekjadon824@gmail.com').first()
if admin:
    superadmin_role = db.query(Role).filter(Role.name == 'superadmin').first()
    if superadmin_role:
        admin.role_id = superadmin_role.id
        db.commit()
        print(f"Success: Upgraded {admin.email} to {superadmin_role.name}!")
    else:
        print("Superadmin role not found!")
else:
    print("Admin not found!")
db.close()
