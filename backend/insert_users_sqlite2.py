import sqlite3
import uuid
import datetime
from app.services.auth_service import get_password_hash

conn = sqlite3.connect('dev.db')
c = conn.cursor()

def upsert(email, password, role):
    h = get_password_hash(password)
    uid = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    
    # check if exists
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET password_hash=?, role=? WHERE email=?", (h, role, email))
    else:
        c.execute("INSERT INTO users (id, email, password_hash, role, first_name, last_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (uid, email, h, role, "Test", "User", now, now))
    
upsert('test_user@example.com', 'User123!@#', 'standard')
upsert('admin@talentops.ai', 'Admin123!@#', 'admin')

conn.commit()
print("Done inserting users")
