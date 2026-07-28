import psycopg

conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
cur = conn.cursor()

cur.execute("SELECT id, email, auth_provider, status FROM users WHERE email = 'admin@talentops.com'")
print('Production DB admin@talentops.com user details:')
print(cur.fetchone())

# Also check for account lockouts
cur.execute("SELECT count(*) FROM login_history WHERE email = 'admin@talentops.com' AND status = 'Failed' AND timestamp >= current_timestamp - interval '15 minutes'")
print(f'Recent failed logins (last 15m): {cur.fetchone()[0]}')

conn.close()
