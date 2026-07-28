import psycopg
import bcrypt

DB1 = 'postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres'
DB2 = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'

def check_db(name, url):
    print(f"\n--- Checking {name} ---")
    try:
        conn = psycopg.connect(url)
        cur = conn.cursor()
        
        cur.execute("SELECT id, email, auth_provider, status, password_hash FROM users WHERE email = 'admin@talentops.com'")
        row = cur.fetchone()
        if row:
            print(f'User found: {row[:4]}')
            
            cur.execute("SELECT count(*) FROM login_history WHERE email = 'admin@talentops.com' AND status = 'Failed' AND timestamp >= current_timestamp - interval '15 minutes'")
            print(f'Recent failed logins: {cur.fetchone()[0]}')
            
            # Update password
            new_hash = bcrypt.hashpw(b'1012', bcrypt.gensalt()).decode('utf-8')
            cur.execute("UPDATE users SET password_hash = %s WHERE email = 'admin@talentops.com'", (new_hash,))
            
            # Clear lockouts
            cur.execute("DELETE FROM login_history WHERE email = 'admin@talentops.com'")
            
            conn.commit()
            print("Password reset to 1012 and login history cleared!")
        else:
            print("User admin@talentops.com NOT FOUND!")
            
        conn.close()
    except Exception as e:
        print(f"Error connecting to {name}: {e}")

check_db("DB1 (qpetz)", DB1)
check_db("DB2 (dcqvs)", DB2)

