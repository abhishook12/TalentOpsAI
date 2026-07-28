import sqlite3
import bcrypt

db_path = 'C:\\TalentOpsAI\\backend\\dev.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

def insert_user(email, password, role):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    try:
        c.execute("INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)", (email, hashed, role))
        print(f"Created {email}")
    except sqlite3.IntegrityError:
        c.execute("UPDATE users SET password_hash=?, role=? WHERE email=?", (hashed, role, email))
        print(f"Updated {email}")

insert_user('test_user@example.com', 'User123!@#', 'standard')
insert_user('admin@talentops.ai', 'Admin123!@#', 'admin')

conn.commit()
conn.close()
