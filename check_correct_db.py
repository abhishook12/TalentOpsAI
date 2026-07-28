import sqlalchemy
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    res = conn.execute(sqlalchemy.text("SELECT count(*) FROM recruiters")).scalar()
    print("Correct DB count:", res)
