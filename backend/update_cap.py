import os, sys
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_URL'))
with e.connect() as c:
  c.execute(text("UPDATE enrichment_runs SET max_updates = 5000 WHERE run_id='full-enrichment-20260623-221909'"))
  c.commit()
  print('Cap updated to 5000')
