import sqlalchemy
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    row = conn.execute(text("SELECT status FROM users WHERE email = 'test3@talentops.com'")).scalar()
    print("User status in DB:", row)
