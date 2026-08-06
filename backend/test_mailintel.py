import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import RecruiterEmail
from app.services.mailintel_engine import process_delivery_event
import time

def test_mailintel():
    db = SessionLocal()
    
    # Fake some delivery events for an existing email
    email_obj = db.query(RecruiterEmail).first()
    if not email_obj:
        print("No emails found to test.")
        return
        
    email_str = email_obj.email
    print(f"Testing with email: {email_str}")
    
    # 1. Simulate delivery
    process_delivery_event(db, email_str, 'delivered', campaign_id=1)
    print("Simulated Delivery")
    
    # 2. Simulate reply
    process_delivery_event(db, email_str, 'replied', campaign_id=1)
    print("Simulated Reply")
    
    # 3. Simulate soft bounce
    process_delivery_event(db, email_str, 'soft_bounce', campaign_id=1)
    print("Simulated Soft Bounce")
    
    # 4. Simulate hard bounce
    process_delivery_event(db, email_str, 'hard_bounce', campaign_id=1, reason="Test Bounce")
    print("Simulated Hard Bounce")
    
    print("MailIntel events processed successfully.")
    
    # Query stats
    from app.models.models import DomainReputation, MailIntelTracking
    dr = db.query(DomainReputation).first()
    print(f"Domain Reputation: {dr.domain} - Score: {dr.reputation_score} - Sent: {dr.total_sent} - Delivered: {dr.total_delivered} - Bounced: {dr.total_bounced} - Replied: {dr.total_replied}")
    
    trk = db.query(MailIntelTracking).filter(MailIntelTracking.email_id == email_obj.id).first()
    print(f"Tracking Info: Hard Bounces: {trk.hard_bounce_count}, Soft Bounces: {trk.soft_bounce_count}")
    
    print(f"Confidence Score: {email_obj.confidence_score}, Status: {email_obj.status}")

if __name__ == "__main__":
    test_mailintel()
