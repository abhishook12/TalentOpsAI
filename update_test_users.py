import os
import sys

os.environ['DATABASE_URL'] = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres'
sys.path.insert(0, 'C:\\TalentOpsAI\\backend')

from app.database import SessionLocal
from app.models.auth_models import User

db = SessionLocal()
for i in range(1, 4):
    user = db.query(User).filter(User.email == f'test_user_{i}@example.com').first()
    if user:
        user.password_hash = '$2b$12$hnFXMx3oq6BlhLxF775lSu8Eu6rzdEA9sQNUNW1pTNpU9eZNgt68i'
        user.status = 'Active'
db.commit()
print('Hashes updated!')
