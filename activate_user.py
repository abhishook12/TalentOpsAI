import sys
import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

sys.path.insert(0, './backend')
from app.database import SessionLocal
from app.models.auth_models import User

email = sys.argv[1]
db = SessionLocal()
u = db.query(User).filter(User.email == email).first()
if u:
    u.status = "Active"
    db.commit()
    print(f"Activated {email}")
else:
    print(f"User {email} not found!")
    sys.exit(1)
db.close()
