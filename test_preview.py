import sys
import os

os.chdir('C:\\TalentOpsAI\\backend')
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.auth_models import User
from app.routes.campaigns import api_prepare_preview, PreparePreviewRequest
from app.models.campaigns import Campaign, SequenceStep, EmailTemplate, CampaignRecruiter, Recruiter

db = SessionLocal()
try:
    user = db.query(User).first()
    if not user:
        user = User(email='test@example.com', hashed_password='xyz', name='Test')
        db.add(user)
        db.commit()
        db.refresh(user)

    campaign = Campaign(
        user_id=user.id,
        name='Test Campaign',
        status='draft',
        from_email='Outlook Default'
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    req = PreparePreviewRequest(
        name='Test Campaign',
        from_email='Outlook Default',
        subject='My Subject',
        body='<p>My Body</p>',
        recipients=[{'email': 'test_rec@example.com', 'name': 'Test Rec'}]
    )

    try:
        res = api_prepare_preview(campaign.campaign_id, req, db, user)
        print("Prepare Preview Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

finally:
    db.close()
