import sys
import os
import time

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.recruiter_store import recruiter_store
from app.services.verification_state import verification_state

def monitor_engines():
    print("=" * 80)
    print("ENGINE MONITORING DASHBOARD")
    print("=" * 80)
    
    recruiter_store._ensure_loaded()
    duck = recruiter_store._conn
    
    while True:
        try:
            # 1. Check Data Filler Progress (Specialization)
            filler_stats = duck.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE specialization IS NOT NULL AND specialization != '' AND LOWER(specialization) NOT IN ('null', 'n/a', 'none', 'unknown')) as filled,
                    COUNT(*) FILTER (WHERE (specialization IS NULL OR specialization = '' OR LOWER(specialization) IN ('null', 'n/a', 'none', 'unknown')) AND title IS NOT NULL AND title != '') as remaining_fillable
                FROM recruiters
            """).fetchone()
            
            total_records = filler_stats[0]
            filled_spec = filler_stats[1]
            remaining_spec = filler_stats[2]
            
            # 2. Check Verification Progress
            v_state = verification_state.get_progress()
            
            print(chr(27) + "[2J") # Clear screen
            print("=" * 80)
            print("LIVE ENGINE STATUS")
            print("=" * 80)
            print(f"Total Records in DB: {total_records:,}")
            print("-" * 80)
            print("DATA FILLER ENGINE (Specializations)")
            print(f"Filled: {filled_spec:,} | Remaining to process: {remaining_spec:,}")
            print(f"Percentage Complete: {(filled_spec / (filled_spec + remaining_spec) * 100) if (filled_spec + remaining_spec) > 0 else 100:.2f}%")
            print("-" * 80)
            print("EMAIL VERIFICATION ENGINE")
            print(f"Status: {'RUNNING' if v_state['is_running'] else 'PAUSED/STOPPED'}")
            print(f"Total Verified: {v_state['total_processed']:,} | Pending: {v_state['total_pending']:,}")
            print(f"Speed: {v_state['speed_emails_per_hour']:,} emails/hr")
            print("=" * 80)
            print("Press Ctrl+C to exit monitoring.")
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nExiting monitor.")
            break
        except Exception as e:
            print(f"Error checking stats: {e}")
            time.sleep(2)

if __name__ == "__main__":
    monitor_engines()
