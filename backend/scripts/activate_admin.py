import os
import sys
from dotenv import load_dotenv

sys.path.append('C:/TalentOpsAI/backend')
load_dotenv('C:/TalentOpsAI/backend/.env')

from sqlalchemy import create_engine, text
remote_url = os.getenv('DATABASE_URL')
if remote_url and remote_url.startswith('postgresql+psycopg://'):
    remote_url = remote_url.replace('postgresql+psycopg://', 'postgresql://')
elif not remote_url:
    remote_url = "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

engine = create_engine(remote_url)
with engine.connect() as conn:
    res = conn.execute(text("SELECT email, status FROM users WHERE email='admin@talentops.com'")).fetchone()
    if res:
        print(f'User: {res[0]}, status: {res[1]}')
        if res[1] != 'Active':
            conn.execute(text("UPDATE users SET status='Active' WHERE email='admin@talentops.com'"))
            conn.commit()
            print('Updated status to Active!')
    else:
        print('Admin user not found!')
