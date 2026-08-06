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
    conn.execute(text("DELETE FROM login_history WHERE email='admin@talentops.com' AND status='failed'"))
    conn.commit()
    print('Cleared failed login history to prevent rate limit lockout.')
