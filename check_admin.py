import sqlalchemy
DATABASE_URL = "postgresql+psycopg://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    res = conn.execute(sqlalchemy.text("SELECT u.id, u.email, r.name as role FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.email = 'admin@talentops.com'")).fetchall()
    print("Admin info:", res)
