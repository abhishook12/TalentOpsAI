from app.database import SessionLocal
from sqlalchemy import text
import pprint

try:
    db = SessionLocal()
    rows = db.execute(text("SELECT pid, state, wait_event_type, wait_event, query, extract(epoch from now() - query_start) as duration FROM pg_stat_activity WHERE state = 'active'")).mappings().all()
    pprint.pprint([dict(r) for r in rows])
except Exception as e:
    print(e)
