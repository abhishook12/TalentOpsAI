import os, sys
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_URL'))
with e.connect() as c:
  res = c.execute(text("SELECT pid, state, wait_event_type, wait_event FROM pg_stat_activity WHERE state != 'idle'")).fetchall()
  for r in res: print(r)
