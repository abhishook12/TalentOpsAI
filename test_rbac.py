from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.auth_models import User, Role
from backend.app.services.auth_service import create_access_token

client = TestClient(app)

print('--- CHECK 1: Unauthorized Access ---')
r1 = client.get('/admin/stats')
print('Status:', r1.status_code)
assert r1.status_code == 401, 'Expected 401 Unauthorized'
print('Pass: Correctly blocked unauthorized access.')

print('\n--- CHECK 2: Normal User Access ---')
db = SessionLocal()

# Find a normal user
normal_role = db.query(Role).filter(Role.name == 'user').first()
normal_user = db.query(User).filter(User.role_id == normal_role.id).first()

if not normal_user:
    print('Warning: No normal user found to test. Creating one...')
    normal_user = User(email='normal@user.com', first_name='Normal', last_name='User', hashed_password='x', role_id=normal_role.id, status='Active')
    db.add(normal_user)
    db.commit()

token = create_access_token({'sub': str(normal_user.id)})
r2 = client.get('/admin/stats', headers={'Authorization': f'Bearer {token}'})
print('Status:', r2.status_code)
assert r2.status_code == 403, 'Expected 403 Forbidden'
print('Pass: Correctly blocked normal user from admin endpoint.')

print('\n--- CHECK 3: Master Admin Access ---')
admin_user = db.query(User).filter(User.email == 'abhishekjadon824@gmail.com').first()
if admin_user:
    token = create_access_token({'sub': str(admin_user.id)})
    r3 = client.get('/admin/stats', headers={'Authorization': f'Bearer {token}'})
    print('Status:', r3.status_code)
    assert r3.status_code == 200, 'Expected 200 OK'
    print('Pass: Master Admin successfully accessed admin endpoint.')
    print('Data returned:', list(r3.json().keys())[:3], '...')
else:
    print('Warning: Master Admin user not found.')

db.close()
print('\nALL CHECKS PASSED!')
