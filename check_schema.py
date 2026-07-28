import sqlalchemy
DATABASE_URL = "postgresql+psycopg://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    print(conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'recruiters'")).fetchall())
