import psycopg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

cur.execute("SELECT password_hash FROM users WHERE email = 'admin@talentops.com'")
hash_in_db = cur.fetchone()[0]

print(f"Hash in DB: {hash_in_db[:15]}...")

# Test 1: with passlib (what backend uses)
try:
    is_valid_passlib = pwd_context.verify('1012', hash_in_db)
    print(f"Passlib verification: {is_valid_passlib}")
except Exception as e:
    print(f"Passlib Error: {e}")

conn.close()
