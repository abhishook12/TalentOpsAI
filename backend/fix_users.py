from app.database import engine
from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("UPDATE users SET status='Active', auth_provider='local' WHERE email IN ('test_user@example.com', 'admin@talentops.ai')"))
    print("Updated users")
