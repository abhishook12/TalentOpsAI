import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import engine
from app.utils.state_mapper import normalize_state
from sqlalchemy import text

def fast_backfill():
    with engine.begin() as conn:
        print("Fetching unique locations from companies...")
        comp_locs = conn.execute(text("SELECT DISTINCT location FROM companies WHERE location IS NOT NULL")).fetchall()
        for row in comp_locs:
            loc = row[0]
            st = normalize_state(loc)
            if st:
                conn.execute(text("UPDATE companies SET state = :state WHERE location = :loc"), {"state": st, "loc": loc})
        
        print("Fetching unique locations from recruiters...")
        rec_locs = conn.execute(text("SELECT DISTINCT location FROM recruiters WHERE location IS NOT NULL")).fetchall()
        for row in rec_locs:
            loc = row[0]
            st = normalize_state(loc)
            if st:
                conn.execute(text("UPDATE recruiters SET state = :state WHERE location = :loc"), {"state": st, "loc": loc})
        
        print("Inheriting company state for recruiters with null location...")
        conn.execute(text("""
            UPDATE recruiters
            SET state = c.state
            FROM companies c
            WHERE recruiters.company_id = c.company_id
              AND (recruiters.location IS NULL OR recruiters.location = '')
              AND c.state IS NOT NULL
        """))
        
        print("Backfill complete.")

if __name__ == "__main__":
    fast_backfill()
