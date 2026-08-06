import os
import sys
from dotenv import load_dotenv

sys.path.append('C:/TalentOpsAI/backend')
load_dotenv('C:/TalentOpsAI/backend/.env')

from sqlalchemy import create_engine, text
remote_url = os.getenv('DATABASE_URL')
if remote_url and remote_url.startswith('postgresql+psycopg://'):
    remote_url = remote_url.replace('postgresql+psycopg://', 'postgresql://')

engine = create_engine(remote_url)
with engine.connect() as conn:
    res = conn.execute(text("SELECT email, status FROM users WHERE email='demo@talentops.ai'")).fetchone()
    if res:
        print(f'User: {res[0]}, status: {res[1]}')
        if res[1] != 'Active':
            conn.execute(text("UPDATE users SET status='Active' WHERE email='demo@talentops.ai'"))
            conn.commit()
            print('Activated demo account!')
    else:
        print('Demo user not found!')
