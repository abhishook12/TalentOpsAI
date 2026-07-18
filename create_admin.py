import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.database import SessionLocal
from backend.app.models.auth_models import User
from backend.app.services.auth_service import get_password_hash

db = SessionLocal()
existing = db.query(User).filter(User.email == 'admin@example.com').first()
if existing:
    existing.password_hash = get_password_hash('adminpass')
    existing.status = 'Active'
    existing.role_id = 1
    print("Updated existing admin")
else:
    new_user = User(
        email='admin@example.com',
        password_hash=get_password_hash('adminpass'),
        first_name='Admin',
        last_name='User',
        role_id=1,
        status='Active'
    )
    db.add(new_user)
    print("Created new admin")
db.commit()
db.close()
