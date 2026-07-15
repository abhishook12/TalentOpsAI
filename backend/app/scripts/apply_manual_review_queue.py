import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import SessionLocal
from sqlalchemy import text

QUEUE_FILE = os.path.join(os.path.dirname(__file__), "outputs", "workbook_review_queue.json")

def main():
    if not os.path.exists(QUEUE_FILE):
        print("Queue file not found.")
        return

    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)

    session = SessionLocal()
    applied_count = 0
    updates = []
    
    for item in queue:
        recruiter_id = item.get("recruiter_id")
        proposed_state = item.get("proposed_state")
        category = item.get("category")
        evidence = item.get("evidence", {})
        
        if proposed_state:
            # We will merge this into metadata_json and update the state
            update_data = {
                "id": recruiter_id,
                "state": proposed_state,
                "state_source": f"auto_applied_review_queue_{category}",
                "state_confidence": "medium",
                "state_reason": item.get("review_reason", "Auto-applied from review queue"),
                "needs_review": False,
                "review_reason": None,
                "last_scan_at": datetime.now(timezone.utc)
            }
            updates.append(update_data)
            applied_count += 1
            
            if len(updates) >= 1000:
                print(f"Applying batch of {len(updates)}...")
                sql = text("""
                    UPDATE recruiters
                    SET state = :state,
                        state_source = :state_source,
                        state_confidence = :state_confidence,
                        state_reason = :state_reason,
                        needs_review = :needs_review,
                        review_reason = :review_reason,
                        last_scan_at = :last_scan_at
                    WHERE recruiter_id = :id
                      AND (state IS NULL OR state = '' OR needs_review = true)
                """)
                session.execute(sql, updates)
                session.commit()
                updates = []

    if updates:
        print(f"Applying final batch of {len(updates)}...")
        sql = text("""
            UPDATE recruiters
            SET state = :state,
                state_source = :state_source,
                state_confidence = :state_confidence,
                state_reason = :state_reason,
                needs_review = :needs_review,
                review_reason = :review_reason,
                last_scan_at = :last_scan_at
            WHERE recruiter_id = :id
              AND (state IS NULL OR state = '' OR needs_review = true)
        """)
        session.execute(sql, updates)
        session.commit()

    print(f"Total applied from review queue: {applied_count}")
    
    # Let's count how many remain empty
    missing = session.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar()
    print(f"Total remaining missing states in database: {missing}")
    session.close()

if __name__ == "__main__":
    main()
