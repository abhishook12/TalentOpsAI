from backend.app.database import SessionLocal
from backend.app.models.auth_models import LoginHistory
import sys

db = SessionLocal()
failures = db.query(LoginHistory).filter(LoginHistory.status == "Failed").delete()
db.commit()
print(f'Cleared {failures} failed login attempts.')
db.close()
