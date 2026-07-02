import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
rows = db.execute(text("""
    SELECT state, location, COUNT(*)
    FROM recruiters
    WHERE is_active = true AND (state IS NULL OR TRIM(state) = '' OR LOWER(state) = 'nan')
    GROUP BY state, location
    ORDER BY COUNT(*) DESC
    LIMIT 25
""")).fetchall()
print("\nTop 25 Unknown State/Location Pairings:")
for st, loc, cnt in rows:
    print(f"State: {repr(st):12} | Location: {repr(loc):45} | Count: {cnt:,}")
db.close()
