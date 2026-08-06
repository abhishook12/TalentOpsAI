import psycopg
import time
import sys

def check_anomalies():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url) as conn:
        with conn.cursor() as cur:
            # Check 1: Mismatched Domains
            cur.execute("""
                SELECT COUNT(*) 
                FROM recruiters r
                JOIN companies c ON r.company_id = c.company_id
                WHERE r.email IS NOT NULL 
                  AND r.email != ''
                  AND c.email_pattern IS NOT NULL 
                  AND c.email_pattern != ''
                  AND SPLIT_PART(r.email, '@', 2) != c.email_pattern
                  AND SPLIT_PART(r.email, '@', 2) NOT LIKE '%.missing.local'
                  AND SPLIT_PART(r.email, '@', 2) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com')
            """)
            mismatched = cur.fetchone()[0]

            # Check 2: Invalid Emails
            cur.execute("SELECT COUNT(*) FROM recruiters WHERE email IS NULL OR email = '' OR email NOT LIKE '%@%.%'")
            invalid_emails = cur.fetchone()[0]

            # Check 3: Duplicate Companies
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT website 
                    FROM companies 
                    WHERE website IS NOT NULL AND website != '' 
                    GROUP BY website 
                    HAVING COUNT(*) > 1
                ) sub
            """)
            duplicate_companies = cur.fetchone()[0]

            if mismatched == 0 and invalid_emails == 0 and duplicate_companies == 0:
                print(f"[SUCCESS] All anomaly counts are exactly 0 (Mismatched: {mismatched}, Invalid Emails: {invalid_emails}, Duplicate Companies: {duplicate_companies})")
                return True
            else:
                print(f"[FAIL] Found anomalies (Mismatched: {mismatched}, Invalid Emails: {invalid_emails}, Duplicate Companies: {duplicate_companies})")
                return False

if __name__ == "__main__":
    success_count = 0
    for i in range(1, 4):
        print(f"--- Verification Check #{i} ---")
        if check_anomalies():
            success_count += 1
        time.sleep(1)
        
    if success_count == 3:
        print("ALL 3 VERIFICATION CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED.")
        sys.exit(1)
