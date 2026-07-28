import psycopg
conn=psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
res = conn.execute("SELECT column_name, character_maximum_length FROM information_schema.columns WHERE table_name = 'recruiters' AND character_maximum_length IS NOT NULL").fetchall()
print(res)
