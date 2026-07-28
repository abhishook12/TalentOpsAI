import sqlalchemy
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    print(conn.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")).fetchall())
