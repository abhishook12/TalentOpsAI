import sys
sys.path.insert(0, r'C:\TalentOpsAI')
from backend.app.services.recruiter_store import recruiter_store
recruiter_store._ensure_loaded()
cur = recruiter_store._conn.cursor()

try:
    r = cur.execute("SELECT COUNT(*) FROM recruiters WHERE TRY_CAST(created_at AS TIMESTAMP) >= CAST(? AS TIMESTAMP)", ['2026-10-27 00:00:00']).fetchone()
    print("TRY_CAST result:", r[0])
except Exception as e:
    print("TRY_CAST error:", e)

try:
    r2 = cur.execute("SELECT COUNT(*) FROM recruiters WHERE created_at >= ?", ['2026-10-27 00:00:00']).fetchone()
    print("String result:", r2[0])
except Exception as e:
    print("String error:", e)
