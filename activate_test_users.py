from sqlalchemy import create_engine, text
DATABASE_URL = 'postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URL, connect_args={'prepare_threshold': None})
with engine.connect() as conn:
    conn.execute(text("UPDATE users SET status = 'Active' WHERE email LIKE 'test_%'"))
    conn.commit()
