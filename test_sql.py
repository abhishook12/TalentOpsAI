import sqlalchemy, time
from sqlalchemy import text
e = sqlalchemy.create_engine('postgresql+psycopg2://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
conn = e.connect()
s=time.time()
conn.execute(text("SELECT c.campaign_id, COUNT(r.campaign_recruiter_id), SUM(CASE WHEN r.status IN ('Sent', 'Delivered', 'Opened', 'Replied', 'Bounced') THEN 1 ELSE 0 END) FROM campaigns c LEFT JOIN campaign_recruiters r ON c.campaign_id = r.campaign_id GROUP BY c.campaign_id")).fetchall()
print(f'Query took {(time.time()-s)*1000:.0f}ms')
