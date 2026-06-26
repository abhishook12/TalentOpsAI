import os, sys, time
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_URL'))
for i in range(20):
  try:
    with e.connect() as c:
      c.execute(text("SET statement_timeout = '60s'"))
      c.execute(text("UPDATE enrichment_runs SET max_updates = 5000 WHERE run_id='full-enrichment-20260623-221909'"))
      c.commit()
    print('Cap updated to 5000')
    break
  except Exception as err:
    print('Retrying:', err)
    time.sleep(2)
