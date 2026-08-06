import os, sys, datetime
from dotenv import load_dotenv
sys.path.append('C:/TalentOpsAI/backend')
load_dotenv('C:/TalentOpsAI/backend/.env')

from sqlalchemy import create_engine, text
remote_url = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')
engine = create_engine(remote_url)

with engine.connect() as conn:
    res = conn.execute(text("SELECT count(*) FROM recruiters WHERE updated_at >= NOW() - INTERVAL '15 minutes'")).scalar()
    print(f'Recruiters enriched/updated in the last 15 minutes: {res}')
