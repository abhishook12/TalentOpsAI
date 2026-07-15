import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

conn = engine.connect()
rows = conn.execute(text("""
    SELECT recruiter_name, linkedin 
    FROM recruiters 
    WHERE is_active = true 
      AND (linkedin IS NULL OR linkedin = '' OR linkedin LIKE '%improving%') 
""")).fetchall()
with open("test_output.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"{r[0]} | {r[1]}\n")
conn.close()
