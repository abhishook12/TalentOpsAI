import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import get_password_hash

db = SessionLocal()

# Force reset password for admin@talentops.com
user = db.query(User).filter(User.email == 'admin@talentops.com').first()
if user:
    user.password_hash = get_password_hash('1012')
    db.commit()
    print("Password reset successfully for admin@talentops.com to '1012'")
else:
    print("User admin@talentops.com not found")

db.close()
