import requests, sqlalchemy, json
from sqlalchemy import text
e = sqlalchemy.create_engine('postgresql+psycopg2://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
conn = e.connect()
res = conn.execute(text("SELECT campaign_id, status FROM campaigns WHERE status='completed' ORDER BY campaign_id DESC LIMIT 1")).fetchone()
cid = res[0]
print('DB Campaign:', cid, '| Status:', res[1])
counts = conn.execute(text(f"SELECT status, COUNT(*) FROM campaign_recruiters WHERE campaign_id={cid} GROUP BY status")).fetchall()
print('DB Recruiters:', counts)
api_res = requests.get('https://talentopsai-1.onrender.com/campaigns').json()
camp = [c for c in api_res if c['campaign_id'] == cid][0]
print('API Stats:', camp['stats'])
