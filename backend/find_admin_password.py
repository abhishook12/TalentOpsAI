from passlib.context import CryptContext
from app.database import SessionLocal
from app.models.auth_models import User

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
test_passwords = ['Admin@123', 'admin123', 'Admin123', '123456', 'password', 'talentops', 'Admin@1234', 'talentops123', 'TalentOps@1', 'admin', 'admin@123', 'Test@123']

db = SessionLocal()
u = db.query(User).filter(User.email == 'admin@talentops.com').first()
full_hash = u.password_hash
db.close()

print(f"Testing {len(test_passwords)} passwords...")
found = False
for pw in test_passwords:
    try:
        result = pwd_context.verify(pw, full_hash)
        print(f'  {pw}: {"✅ MATCH" if result else "❌"}')
        if result:
            found = True
            print(f"\n=== ADMIN PASSWORD FOUND: {pw} ===")
            break
    except Exception as e:
        print(f'  {pw}: ERROR - {e}')

if not found:
    print("\nNo password matched. Need to reset admin password.")
