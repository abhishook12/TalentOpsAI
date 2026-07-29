import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("SELECT state, COUNT(*) FROM recruiters GROUP BY state ORDER BY COUNT(*) DESC LIMIT 10")).fetchall()
null_count = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar()

print("Top 10 States Distribution:")
for row in res:
    print(f"  {row[0]}: {row[1]}")
print(f"\nRecruiters with NULL/Empty state: {null_count}")
