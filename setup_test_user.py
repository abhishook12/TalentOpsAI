import sys
from backend.app.database import SessionLocal
from backend.app.models.auth_models import User

email = sys.argv[1]
db = SessionLocal()
try:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            first_name="Test",
            last_name="User",
            email=email,
            password_hash="$2b$12$R.3.sZ/Uj.hUa2R4G3/kKOFnNn./U8n/b4MvH8Q7hS9bS8M5v.sO.", # 'StrongPass_2026!'
            status="Active"
        )
        db.add(user)
    else:
        user.status = "Active"
    db.commit()
    print("User setup complete.")
finally:
    db.close()
