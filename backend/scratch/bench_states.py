import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store
import time

recruiter_store._ensure_loaded()
conn = recruiter_store._conn

t0 = time.time()
r1 = conn.execute("""
    SELECT
        state,
        COUNT(*) AS count
    FROM recruiters
    WHERE state IS NOT NULL AND state != '' AND state != 'US'
    GROUP BY state
    ORDER BY count DESC, state ASC
""").fetchall()
t1 = time.time()

t2 = time.time()
r2 = conn.execute("""
    SELECT
        state_upper AS state,
        SUM(recruiter_count) AS count
    FROM company_summary
    WHERE state_upper IS NOT NULL AND state_upper != '' AND state_upper != 'US' AND state_upper != 'UNKNOWN'
    GROUP BY state_upper
    ORDER BY count DESC, state ASC
""").fetchall()
t3 = time.time()

print(f"Full scan time: {(t1-t0)*1000:.2f}ms, results: {len(r1)}")
print(f"Summary table time: {(t3-t2)*1000:.2f}ms, results: {len(r2)}")
print("Summary top 10:", r2[:10])
