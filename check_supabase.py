import psycopg
conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
print("Supabase recent:")
print(conn.execute("SELECT COUNT(*) FROM recruiters WHERE created_at >= NOW() - INTERVAL '2 days'").fetchone())
