import sys
import time
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, CampaignRecruiter
from sqlalchemy import func, case
import uuid

def simulate_heavy_load():
    db = SessionLocal()
    
    # Create a dummy user
    dummy_email = f"test_{uuid.uuid4()}@example.com"
    user = User(email=dummy_email, hashed_password="pwd", full_name="Test")
    db.add(user)
    db.commit()
    
    try:
        # Create 10 campaigns, each with 5000 recipients
        print("Seeding dummy data (10 campaigns, 50,000 recruiters)...")
        campaigns = []
        for i in range(10):
            c = Campaign(user_id=user.id, name=f"Test Campaign {i}")
            db.add(c)
            campaigns.append(c)
        db.commit()
        
        # Insert recruiters fast
        recs = []
        for c in campaigns:
            for j in range(5000):
                recs.append(CampaignRecruiter(
                    campaign_id=c.campaign_id,
                    recruiter_id=1,  # dummy foreign key, might fail if strict FK. We'll set null if possible, or create 1 recruiter
                    status="Sent" if j % 2 == 0 else "Pending"
                ))
        
        # Actually, let's create 1 dummy recruiter
        from app.models.models import Recruiter
        r = Recruiter(user_id=user.id, email="dummy_rec@example.com", recruiter_name="Dummy")
        db.add(r)
        db.commit()
        
        for rec in recs:
            rec.recruiter_id = r.recruiter_id
            
        db.bulk_save_objects(recs)
        db.commit()
        
        print("Data seeded. Testing main query...")
        
        start = time.time()
        base_query = db.query(Campaign).filter(Campaign.user_id == user.id)
        
        query = db.query(
            Campaign,
            func.count(CampaignRecruiter.campaign_recruiter_id).label('total'),
            func.sum(case((CampaignRecruiter.status.in_(['Sent', 'Delivered', 'Opened', 'Replied', 'Bounced']), 1), else_=0)).label('sent'),
            func.sum(case((CampaignRecruiter.status == 'Failed', 1), else_=0)).label('failed')
        ).outerjoin(CampaignRecruiter, Campaign.campaign_id == CampaignRecruiter.campaign_id)
        
        query = query.filter(Campaign.user_id == user.id)
        results = query.group_by(Campaign.campaign_id).order_by(Campaign.created_at.desc()).limit(50).all()
        
        latency = (time.time() - start) * 1000
        print(f"Latency for {len(results)} campaigns: {latency:.2f} ms")
        
        # Test optimized query
        start2 = time.time()
        camps = base_query.order_by(Campaign.created_at.desc()).limit(50).all()
        camp_ids = [c.campaign_id for c in camps]
        stats = db.query(
            CampaignRecruiter.campaign_id,
            func.count(CampaignRecruiter.campaign_recruiter_id).label('total')
        ).filter(CampaignRecruiter.campaign_id.in_(camp_ids)).group_by(CampaignRecruiter.campaign_id).all()
        latency2 = (time.time() - start2) * 1000
        print(f"Latency for optimized approach: {latency2:.2f} ms")
        
    finally:
        # Cleanup
        print("Cleaning up...")
        db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id.in_([c.campaign_id for c in campaigns])).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.user_id == user.id).delete(synchronize_session=False)
        db.query(Recruiter).filter(Recruiter.user_id == user.id).delete(synchronize_session=False)
        db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
        db.commit()
        db.close()

if __name__ == "__main__":
    simulate_heavy_load()
