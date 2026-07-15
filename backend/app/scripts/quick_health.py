import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

conn = engine.connect()
db = conn.execute(text('SELECT pg_database_size(current_database()) / (1024 * 1024)')).fetchone()
health = conn.execute(text("""
    SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') as phone_present,
        COUNT(*) FILTER (WHERE linkedin IS NOT NULL AND linkedin != '') as li_present,
        COUNT(*) FILTER (WHERE location IS NOT NULL AND location != '') as loc_present
    FROM recruiters WHERE is_active = true
""")).fetchone()
print(f"DB Size: {db[0]} MB")
print(f"Total Active: {health[0]}")
print(f"Phone: {health[1]} / {health[0]} ({round(health[1]/health[0]*100,1)}%)")
print(f"LinkedIn: {health[2]} / {health[0]} ({round(health[2]/health[0]*100,1)}%)")
print(f"Location: {health[3]} / {health[0]} ({round(health[3]/health[0]*100,1)}%)")
conn.close()
