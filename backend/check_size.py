import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
print("DB Size:", cur.fetchone()[0])
cur.close()
conn.close()
