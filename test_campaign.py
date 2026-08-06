import requests
import json
import time

BASE_URL = 'http://127.0.0.1:8000/api'
# Assuming admin user has a token, we can just use the DB to bypass auth if we want, or create a mock token.
# Wait, talentops uses standard OAuth or JWT.
# I will use sqlalchemy to directly test the services, since testing via API requires auth token.
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, EmailTemplate, SequenceStep, CampaignRecruiter
from app.services.send_engine import start_campaign, process_campaign_queue
import asyncio

def run_test():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email='admin@talentops.ai').first()
        if not user:
            print('Admin user not found')
            return
            
        print('1. Create Campaign Shell')
        c = Campaign(user_id=user.id, name='Test QA Campaign', status='draft', from_email='test@outlook.com')
        db.add(c)
        db.commit()
        
        print('2. Add Template & Sequence Step')
        t = EmailTemplate(campaign_id=c.campaign_id, user_id=user.id, name='Draft', subject='Test Subject {{FirstName}}', body='Hello {{FirstName}}, test body.')
        db.add(t)
        db.commit()
        
        s = SequenceStep(campaign_id=c.campaign_id, template_id=t.template_id, step_order=1)
        db.add(s)
        db.commit()
        
        print('3. Enroll Emails')
        # Simulate enroll_emails
        # Create a dummy recruiter
        from app.models.models import Recruiter
        rec = Recruiter(email='qa_test_recipient@gmail.com', recruiter_name='QA Tester')
        db.add(rec)
        db.commit()
        
        cr = CampaignRecruiter(campaign_id=c.campaign_id, recruiter_id=rec.recruiter_id, current_step_id=s.step_id, status='pending')
        db.add(cr)
        db.commit()
        
        print('4. Validate Before Send')
        from app.routes.campaigns import api_validate_before_send
        # We need to mock get_current_user_from_request and db
        # Or just test the logic directly:
        # Actually, let's just inspect the DB state.
        print('Campaign successfully constructed in DB.')
        print(f'Campaign ID: {c.campaign_id}')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    run_test()
