import sys
import psycopg

db_url = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def check_db():
    try:
        conn = psycopg.connect(db_url)
        cur = conn.cursor()
        
        email = "uat_test_1784228866643@talentops.com"
        
        # Check users table
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if user:
            print(f"[OK] Found user in database: {user[0]}")
        else:
            print("[FAIL] User not found in database.")
            
        # Check visitor_sessions table
        cur.execute("SELECT session_id FROM visitor_sessions WHERE user_email = %s", (email,))
        sessions = cur.fetchall()
        if sessions:
            print(f"[OK] Found {len(sessions)} analytics sessions for user.")
        else:
            print("[FAIL] No analytics sessions found for user.")
            
        # Check action_logs table
        cur.execute("SELECT action_type FROM action_logs WHERE user_email = %s", (email,))
        actions = cur.fetchall()
        if actions:
            print(f"[OK] Found {len(actions)} action logs for user.")
        else:
            print("[FAIL] No action logs found for user.")
            
        # Check page_visits table
        cur.execute("SELECT path FROM page_visits WHERE user_email = %s", (email,))
        visits = cur.fetchall()
        if visits:
            print(f"[OK] Found {len(visits)} page visits for user.")
        else:
            print("[FAIL] No page visits found for user.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
