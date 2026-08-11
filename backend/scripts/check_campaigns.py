import psycopg
import os
from dotenv import load_dotenv

load_dotenv("C:/TalentOpsAI/backend/.env")
db_url = os.environ["DATABASE_URL"].replace("+psycopg", "")
conn = psycopg.connect(db_url)
cols = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'campaigns'").fetchall()
print("Columns:", [c[0] for c in cols])
