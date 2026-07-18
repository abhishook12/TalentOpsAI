import psycopg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
db_url = os.getenv('DATABASE_URL')
# psycopg format: postgresql://...
db_url = db_url.replace('postgresql+psycopg', 'postgresql')

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, email, role_id, status FROM users LIMIT 10")
        rows = cur.fetchall()
        for row in rows:
            print(row)
