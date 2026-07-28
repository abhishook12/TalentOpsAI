import os
os.environ['DATABASE_URL'] = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
import sys
sys.path.insert(0, "C:\\TalentOpsAI\\backend")
from app.database import SessionLocal
from app.models.auth_models import LoginHistory
db = SessionLocal()
try:
    db.query(LoginHistory).filter(LoginHistory.status == 'Failed').delete()
    db.commit()
    print('Cleared failed logins!')
except Exception as e:
    print(e)
