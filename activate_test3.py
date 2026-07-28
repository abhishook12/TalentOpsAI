import sqlalchemy
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    print("Activating test3...")
    conn.execute(text("UPDATE users SET status = 'Active' WHERE email = 'test3@talentops.com'"))
    conn.commit()
    print("Activated.")
