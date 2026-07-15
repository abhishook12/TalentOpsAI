from app.database import SessionLocal
from sqlalchemy import text

try:
    db = SessionLocal()
    rows = db.execute(text("SELECT pid FROM pg_stat_activity WHERE state='active' AND pid != pg_backend_pid() AND extract(epoch from now() - query_start) > 10")).mappings().all()
    for row in rows:
        print(f"Killing pid {row['pid']}")
        db.execute(text(f"SELECT pg_terminate_backend({row['pid']})"))
    db.commit()
    print("Done killing hanging queries.")
except Exception as e:
    print(e)
