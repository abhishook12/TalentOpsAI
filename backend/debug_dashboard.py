import traceback
from app.database import SessionLocal
from app.routes.analytics import get_visit_stats

db = SessionLocal()
try:
    print(get_visit_stats(db))
except Exception as e:
    traceback.print_exc()
