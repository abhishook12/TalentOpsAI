import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')
# Override DATABASE_URL to Prod
os.environ['DATABASE_URL'] = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

import sys
sys.path.append('C:\\TalentOpsAI\\backend')
from app.database import get_db
from app.routes.bridge import get_bridge_tasks

db = next(get_db())
try:
    print(get_bridge_tasks(db=db))
except Exception as e:
    import traceback
    traceback.print_exc()
