import os, sys
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_URL'))
with e.connect() as c:
  c.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND state = 'idle in transaction'"))
  c.commit()
  print('Locks cleared.')
