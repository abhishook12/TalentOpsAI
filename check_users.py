import sqlite3
conn = sqlite3.connect('backend/dev.db')
c = conn.cursor()
c.execute("SELECT id, email, status FROM users WHERE email LIKE 'googleuser_%' ORDER BY id DESC LIMIT 5")
for row in c.fetchall():
    print(row)

c.execute("SELECT id, device_name, user_id, status FROM trusted_devices ORDER BY id DESC LIMIT 5")
print("\nDevices:")
for row in c.fetchall():
    print(row)
conn.close()
