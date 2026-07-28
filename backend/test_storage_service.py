from app.database import SessionLocal
from app.services.storage_limit_service import get_storage_health
import json

db = SessionLocal()
try:
    health = get_storage_health(db)
    print(json.dumps(health, indent=2))
finally:
    db.close()
