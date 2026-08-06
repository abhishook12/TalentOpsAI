import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import verify_password

db = SessionLocal()

# Get all users
users = db.query(User).filter(User.status == 'Active').all()

print(f"Found {len(users)} active users:")
for u in users[:15]:
    role_name = u.role_obj.name if hasattr(u, 'role_obj') and u.role_obj else getattr(u, 'role_id', 'N/A')
    print(f"  id={u.id} email={u.email} role_id={u.role_id} status={u.status} auth_provider={getattr(u, 'auth_provider', 'N/A')} has_pw={'YES' if u.password_hash else 'NO'}")
    # Try common passwords
    if u.password_hash:
        for pwd in ['1012', 'admin', 'password', '10dec2000', 'Admin@1012', 'Admin1012!', 'Abhishek@1012', 'Technovion@1012']:
            try:
                if verify_password(pwd, u.password_hash):
                    print(f"    >>> PASSWORD MATCH: {pwd}")
                    break
            except:
                pass

db.close()
