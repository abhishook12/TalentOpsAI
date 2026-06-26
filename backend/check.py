import os, sys
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_URL'))
with e.connect() as c:
  print(c.execute(text("SELECT MAX(recruiter_id), COUNT(*) FROM enrichment_results WHERE run_id='full-enrichment-20260623-221909'")).fetchone())
