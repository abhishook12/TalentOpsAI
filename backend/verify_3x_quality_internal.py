import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.routes.analytics import get_quality_metrics, get_repair_logs
from app.models.auth_models import User

def verify(attempt, db, mock_user):
    print(f"\n--- Attempt {attempt} ---")
    
    # 1. Check quality-metrics
    try:
        data = get_quality_metrics(db=db, current_user=mock_user)
        print(f"PASS Quality Metrics OK: Health={data.get('overall_health')}%")
    except Exception as e:
        print(f"FAIL Quality Metrics Error: {e}")
        return False
        
    # 2. Check repair-logs
    try:
        data = get_repair_logs(limit=5, db=db, current_user=mock_user)
        print(f"PASS Repair Logs OK: Count={len(data.get('logs', []))}")
    except Exception as e:
        print(f"FAIL Repair Logs Error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    db = SessionLocal()
    mock_user = User(id=1, email="admin@talentops.com")
    
    successes = 0
    for i in range(1, 4):
        if verify(i, db, mock_user):
            successes += 1
        time.sleep(1)

    print("\n=== FINAL RESULT ===")
    if successes == 3:
        print("SUCCESS: Verified 3 times successfully.")
    else:
        print(f"FAILURE: Only verified {successes}/3 times successfully.")
    db.close()
