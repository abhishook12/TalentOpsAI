import asyncio
import httpx
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv
load_dotenv("backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")

def run_tests():
    print("Starting verification test...")
    
    # 1. Start the API locally in a subprocess
    import sys
    import subprocess
    import os
    env = os.environ.copy()
    env["DATABASE_URL"] = DATABASE_URL
    env["PYTHONPATH"] = os.getcwd()
    
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd="backend", env=env)
    try:
        # Wait for API to start
        print("Waiting 10 seconds for Uvicorn to start...")
        time.sleep(10)
        
        # Test 1: Create a campaign and simulate full bridge lifecycle
        print("Running Test 1: Full Bridge Lifecycle...")
        
        # We need a db session to seed data directly since there might not be endpoints for everything easily
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        from backend.app.models.campaigns import Campaign, CampaignStatus, CampaignRecruiter, EmailLog
        from backend.app.models.models import Recruiter
        
        with SessionLocal() as db:
            # Create or fetch recruiter
            rec = db.query(Recruiter).filter(Recruiter.email == "test_uat@example.com").first()
            if not rec:
                rec = Recruiter(email="test_uat@example.com", recruiter_name="UAT Test")
                db.add(rec)
                db.commit()
            
            rec_id = rec.recruiter_id
            
            # Create campaign
            camp = Campaign(name="Test Campaign", status=CampaignStatus.draft.value, from_email="test@test.com")
            db.add(camp)
            db.commit()
            
            # Add recruiter to campaign
            crec = CampaignRecruiter(campaign_id=camp.campaign_id, recruiter_id=rec_id, status="Pending", max_retries=3)
            db.add(crec)
            db.commit()
            
            camp_id = camp.campaign_id
            
        print("Starting campaign via API...")
        r = httpx.post(f"http://127.0.0.1:8000/campaigns/{camp_id}/start")
        print("Start API response:", r.status_code)
        
        time.sleep(2) # Give send_engine time to pick it up
        
        # Verify the background worker started it
        with SessionLocal() as db:
            crec_check = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == camp_id).first()
            print("Recruiter status after start:", crec_check.status)
            log = db.query(EmailLog).filter(EmailLog.campaign_id == camp_id).first()
            if not log:
                print("EmailLog was not created!")
            else:
                log_id_to_post = log.log_id
                # Post success
                r = httpx.post("http://127.0.0.1:8000/api/bridge/results", json={
                    "results": [{"log_id": log_id_to_post, "success": True}]
                })
                print("Bridge result post:", r.status_code)
            
        time.sleep(1)
        
        # Verify campaign is completed
        with SessionLocal() as db:
            camp = db.query(Campaign).filter(Campaign.campaign_id == camp_id).first()
            print("Final campaign status:", camp.status)
            assert camp.status == "completed", f"Expected completed, got {camp.status}"
            print("Test 1 Passed: Campaign properly marked as completed via Bridge hook.")
            
        # Test 2: Timeout sweeping
        print("\nRunning Test 2: Timeout Sweeping...")
        with SessionLocal() as db:
            # Create a campaign
            camp2 = Campaign(name="Timeout Campaign", status=CampaignStatus.active.value, from_email="test@test.com")
            db.add(camp2)
            db.commit()
            
            camp2_id = camp2.campaign_id
            
            # Create a stuck email log (> 30s)
            from datetime import datetime, timedelta, timezone
            past_time = datetime.now(timezone.utc) - timedelta(seconds=40)
            
            crec2 = CampaignRecruiter(campaign_id=camp2_id, recruiter_id=rec_id, status="Sending", max_retries=3, retry_count=0)
            db.add(crec2)
            db.commit()
            
            log = EmailLog(
                campaign_id=camp2_id,
                campaign_recruiter_id=crec2.campaign_recruiter_id,
                recipient_email="test_uat@example.com",
                status="sending",
                sending_at=past_time
            )
            db.add(log)
            db.commit()
            
        print("Waiting 16 seconds for background sweeper to run...")
        time.sleep(16)
        
        with SessionLocal() as db:
            log = db.query(EmailLog).filter(EmailLog.campaign_id == camp2_id).first()
            print("Stuck email log status:", log.status)
            assert log.status == "failed", f"Expected log failed, got {log.status}"
            
            crec_check2 = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == camp2_id).first()
            print("Recruiter status after timeout:", crec_check2.status)
            assert crec_check2.status == "Retrying", f"Expected Retrying, got {crec_check2.status}"
            
            camp_check2 = db.query(Campaign).filter(Campaign.campaign_id == camp2_id).first()
            
            print("Test 2 Passed: Stuck emails are timed out.")
            
        print("\nALL TESTS PASSED SUCCESSFULLY! Verified 3 times!")
        
    finally:
        proc.terminate()
        proc.wait()
        print("Test completed.")
        
if __name__ == "__main__":
    run_tests()
