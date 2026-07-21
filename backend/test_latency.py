import time
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, CampaignRecruiter
from sqlalchemy import func, case

def test_campaign_list_latency():
    print("Testing campaign list latency...")
    db = SessionLocal()
    try:
        # Assuming user_id = 1 for testing (get an existing user)
        user = db.query(User).first()
        if not user:
            print("No user found in DB to test with.")
            return

        user_id = user.id
        print(f"Testing with user_id: {user_id}")

        start = time.time()
        
        # EXACT QUERY USED IN campaigns.py list_campaigns endpoint
        base_query = db.query(Campaign).filter(Campaign.user_id == user_id)
        base_query = base_query.filter(Campaign.is_archived.is_(False))
        total_count = base_query.with_entities(func.count(Campaign.campaign_id)).scalar()
            
        query = db.query(
            Campaign,
            func.count(CampaignRecruiter.campaign_recruiter_id).label('total'),
            func.sum(case((CampaignRecruiter.status.in_(['Sent', 'Delivered', 'Opened', 'Replied', 'Bounced']), 1), else_=0)).label('sent'),
            func.sum(case((CampaignRecruiter.status == 'Failed', 1), else_=0)).label('failed')
        ).outerjoin(CampaignRecruiter, Campaign.campaign_id == CampaignRecruiter.campaign_id)
        
        query = query.filter(Campaign.user_id == user_id)
        query = query.filter(Campaign.is_archived.is_(False))
            
        results = query.group_by(Campaign.campaign_id).order_by(Campaign.created_at.desc()).offset(0).limit(50).all()
        
        end = time.time()
        latency_ms = (end - start) * 1000
        
        print(f"Total count: {total_count}")
        print(f"Results fetched: {len(results)}")
        print(f"Latency: {latency_ms:.2f} ms")
        
        if latency_ms < 500:
            print("Check 2: Pass. Latency is well under 500ms.")
        else:
            print("Check 2: Warning! Latency might be high.")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_campaign_list_latency()
