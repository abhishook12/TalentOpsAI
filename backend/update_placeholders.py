import psycopg, os
from dotenv import load_dotenv
load_dotenv('.env')
conn = psycopg.connect(os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://'), prepare_threshold=None)
cur=conn.cursor()
cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE email_status = 'unknown' AND (email ILIKE '%%missing.local' OR email ILIKE '%%invalid.local')")
conn.commit()
print(cur.rowcount, 'updated')
