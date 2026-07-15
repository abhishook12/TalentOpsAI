import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE recruiter_name IS NOT NULL AND recruiter_name != '') as name,
            COUNT(*) FILTER (WHERE company_id IS NOT NULL) as company,
            COUNT(*) FILTER (WHERE email IS NOT NULL AND email != '') as email,
            COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') as phone,
            COUNT(*) FILTER (WHERE linkedin IS NOT NULL AND linkedin != '') as linkedin,
            COUNT(*) FILTER (WHERE location IS NOT NULL AND location != '') as location,
            COUNT(*) FILTER (WHERE state IS NOT NULL AND state != '') as state,
            COUNT(*) FILTER (WHERE normalized_city IS NOT NULL AND normalized_city != '') as city
        FROM recruiters WHERE is_active = true
    """)).fetchone()

    print(f"Total:    {r[0]}")
    print(f"Name:     {r[1]} ({round(r[1]/r[0]*100,1)}%)")
    print(f"Company:  {r[2]} ({round(r[2]/r[0]*100,1)}%)")
    print(f"Email:    {r[3]} ({round(r[3]/r[0]*100,1)}%)")
    print(f"Phone:    {r[4]} ({round(r[4]/r[0]*100,1)}%)")
    print(f"LinkedIn: {r[5]} ({round(r[5]/r[0]*100,1)}%)")
    print(f"Location: {r[6]} ({round(r[6]/r[0]*100,1)}%)")
    print(f"State:    {r[7]} ({round(r[7]/r[0]*100,1)}%)")
    print(f"City:     {r[8]} ({round(r[8]/r[0]*100,1)}%)")
