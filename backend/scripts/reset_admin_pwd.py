import psycopg
import sys
sys.path.append('C:/TalentOpsAI/backend')
from psycopg.rows import dict_row
from app.services.auth_service import get_password_hash

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

print("Connecting to DB to update admin password...")
try:
    with psycopg.connect(DB_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            hashed_pwd = get_password_hash("admin123456")
            cur.execute("""
                UPDATE users SET password_hash = %s WHERE email = 'admin@talentops.com';
            """, (hashed_pwd,))
            conn.commit()
            print("Password for admin@talentops.com updated successfully.")
except Exception as e:
    print("Failed:", e)
