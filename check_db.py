import sqlite3
import json

conn = sqlite3.connect('backend/data/talentops.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

users = [dict(r) for r in cur.execute("SELECT * FROM users WHERE email LIKE '%bsen%'").fetchall()]
print('Users:', json.dumps(users, indent=2, default=str))

devices = [dict(r) for r in cur.execute("SELECT * FROM trusted_devices").fetchall()]
print(f'Total devices: {len(devices)}')

pending_devices = [dict(r) for r in cur.execute("SELECT * FROM trusted_devices WHERE status='Pending'").fetchall()]
print(f'Pending devices: {len(pending_devices)}')

if users:
    user_id = users[0]['id']
    user_devices = [dict(r) for r in cur.execute(f"SELECT * FROM trusted_devices WHERE user_id={user_id}").fetchall()]
    print(f'Devices for {users[0]["email"]}:', json.dumps(user_devices, indent=2, default=str))
