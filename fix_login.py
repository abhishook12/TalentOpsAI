import sys
sys.path.append(r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Role
from app.services.auth_service import get_password_hash

db = SessionLocal()
try:
    # Step 1: Create Admin role if it doesn't exist
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Full admin access")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
        print(f"Created 'admin' role with id={admin_role.id}")
    else:
        print(f"Admin role already exists with id={admin_role.id}")

    # Step 2: Create or update admin user with proper role
    user = db.query(User).filter(User.email == "admin@talentops.com").first()
    if not user:
        user = User(
            email="admin@talentops.com",
            first_name="Admin",
            last_name="User",
            password_hash=get_password_hash("1012"),
            role_id=admin_role.id,
            status="Active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Admin user created with id={user.id}")
    else:
        user.password_hash = get_password_hash("1012")
        user.role_id = admin_role.id
        db.commit()
        print(f"Admin user updated: id={user.id}, role_id={user.role_id}")

    # Step 3: Auto-trust ALL devices for this user
    from app.models.auth_models import TrustedDevice
    devices = db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id).all()
    for d in devices:
        old_status = d.status
        d.status = "Trusted"
        d.approved_by = user.id
        print(f"  Auto-trusted device: {d.device_id_hash[:16]}... (was {old_status})")
    db.commit()
    print(f"Trusted {len(devices)} device(s)")

    if len(devices) == 0:
        print("No devices found yet - they will be auto-trusted on next login since user has admin role")

    print("\nDONE. Login with admin@talentops.com / 1012")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
finally:
    db.close()
