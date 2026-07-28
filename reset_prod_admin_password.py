import psycopg
import bcrypt

new_hash = bcrypt.hashpw(b'1012', bcrypt.gensalt()).decode('utf-8')

conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

cur.execute("UPDATE users SET password_hash = %s WHERE email = 'admin@talentops.com'", (new_hash,))
conn.commit()

print("Production admin password successfully reset to 1012!")

conn.close()
