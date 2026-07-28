from app.database import engine
from sqlalchemy import text
import datetime

def upsert(email, h, role_id):
    now = datetime.datetime.now().isoformat()
    with engine.begin() as conn:
        res = conn.execute(text("SELECT id FROM users WHERE email=:email"), {"email": email}).fetchone()
        if res:
            conn.execute(text("UPDATE users SET password_hash=:h, role_id=:role_id WHERE email=:email"), {"h": h, "role_id": role_id, "email": email})
            print("Updated", email)
        else:
            conn.execute(text("INSERT INTO users (email, password_hash, role_id, first_name, last_name, created_at, updated_at) VALUES (:email, :h, :role_id, :fn, :ln, :now, :now)"),
                         {"email": email, "h": h, "role_id": role_id, "fn": "Test", "ln": "User", "now": now})
            print("Inserted", email)

upsert('test_user@example.com', '$2b$10$mdOB65eDDAb/jBe5T9vJHOBFhq8jfAkrhRTQy3QDn0p9CrswRv7sC', 2)
upsert('admin@talentops.ai', '$2b$10$k92mzUOe.bJeSlu5dSWKS.d4K4TyZebckNO9iPUzh2wBN7aWLf8gm', 1)
