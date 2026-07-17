from backend.app.database import SessionLocal
from backend.app.models.auth_models import User
from backend.app.services.auth_service import get_password_hash

db = SessionLocal()
admin = db.query(User).filter(User.email == 'abhishekjadon824@gmail.com').first()
if admin:
    admin.password_hash = get_password_hash('Admin@1234')
    db.commit()
    print('Password reset to Admin@1234')
db.close()
