import psycopg

conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

cur.execute("SELECT timestamp, status, reason FROM login_history WHERE email = 'admin@talentops.com' ORDER BY timestamp DESC LIMIT 10")
for row in cur.fetchall():
    print(row)

# Also clear the login history for this user so they can log in
cur.execute("DELETE FROM login_history WHERE email = 'admin@talentops.com'")
conn.commit()
print("Login history cleared.")

conn.close()
