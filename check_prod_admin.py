import psycopg
conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()
cur.execute("SELECT id, email, first_name, role_id, status, password_hash FROM users WHERE email = 'admin@talentops.com'")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"ID: {r[0]}, Email: {r[1]}, Name: {r[2]}, Role: {r[3]}, Status: {r[4]}, PW Hash present: {bool(r[5])}")
else:
    print("NO ADMIN USER FOUND IN PROD DB!")

# Check if there's any superadmin
cur.execute("SELECT id, email, first_name, role_id, status FROM users WHERE role_id = 1")
print("\nSuperadmins:")
for r in cur.fetchall():
    print(f"  ID: {r[0]}, Email: {r[1]}, Name: {r[2]}, Status: {r[4]}")

# Check table structure - does trusted_devices exist?
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
print("\nTables in Prod DB:")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
