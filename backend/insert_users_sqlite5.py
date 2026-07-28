import sqlite3
import datetime

conn = sqlite3.connect('dev.db')
c = conn.cursor()

def upsert(email, h, role_id):
    now = datetime.datetime.now().isoformat()
    
    # check if exists
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET password_hash=?, role_id=? WHERE email=?", (h, role_id, email))
    else:
        c.execute("INSERT INTO users (email, password_hash, role_id, first_name, last_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (email, h, role_id, "Test", "User", now, now))
    
upsert('test_user@example.com', '$2b$10$mdOB65eDDAb/jBe5T9vJHOBFhq8jfAkrhRTQy3QDn0p9CrswRv7sC', 2)
upsert('admin@talentops.ai', '$2b$10$k92mzUOe.bJeSlu5dSWKS.d4K4TyZebckNO9iPUzh2wBN7aWLf8gm', 1)

conn.commit()
print("Done")
