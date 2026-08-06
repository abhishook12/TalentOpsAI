import psycopg

GENERIC_NAMES = [
    'Unknown',
    'Partner',
    'Unknown Recruiter',
    'Unknown Vaco Recruiter',
    'Recruiter',
    'Talent Acquisition',
    'HR',
    'Human Resources'
]

def clean_postgres():
    print("\\n--- Cleaning Postgres (aws-1) ---")
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url) as conn:
        with conn.cursor() as cur:
            # 1. Delete missing email AND phone
            cur.execute("DELETE FROM recruiters WHERE (email IS NULL OR email = '') AND (phone IS NULL OR phone = '')")
            missing_deleted = cur.rowcount
            
            # 2. Delete generic names
            placeholders = ','.join(f"'{name}'" for name in GENERIC_NAMES)
            cur.execute(f"DELETE FROM recruiters WHERE recruiter_name IN ({placeholders})")
            generic_deleted = cur.rowcount
            
            # 3. Delete "Unknown %" names
            cur.execute("DELETE FROM recruiters WHERE recruiter_name ILIKE 'Unknown %'")
            unknown_deleted = cur.rowcount
            
            print(f"Deleted {missing_deleted} recruiters missing both email and phone.")
            print(f"Deleted {generic_deleted + unknown_deleted} recruiters with generic names.")
            
        conn.commit()

if __name__ == "__main__":
    clean_postgres()
