import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

import asyncio
from app.database import SessionLocal
from app.routes.recruiters import get_recruiters
from app.models.auth_models import User
import math

class DummyResponse:
    def __init__(self):
        self.headers = {}

async def test_endpoint():
    db = SessionLocal()
    user = User(id=1, email="test@test.com")
    response = DummyResponse()
    
    try:
        res = get_recruiters(
            response=response,
            page=1,
            limit=5,
            company_id=129651,
            db=db,
            current_user=user
        )
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_endpoint())
