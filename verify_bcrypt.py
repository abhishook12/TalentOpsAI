import psycopg
import bcrypt

conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

cur.execute("SELECT password_hash FROM users WHERE email = 'admin@talentops.com'")
hash_in_db = cur.fetchone()[0]
print(f'Hash: {hash_in_db}')
try:
    print(f'bcrypt check: {bcrypt.checkpw(b"1012", hash_in_db.encode("utf-8"))}')
except Exception as e:
    print(f'Error: {e}')
conn.close()
