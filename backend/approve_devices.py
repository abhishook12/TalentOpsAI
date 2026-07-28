from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("UPDATE trusted_devices SET status='Approved'"))
    print("Approved devices")
