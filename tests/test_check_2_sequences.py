"""
Test Check 2: Multi-Touch Sequence Execution & Scheduler Verification
Tests step progression logic, delay calculation, finalization guard, reply detection auto-halt, and scheduler queueing.
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from datetime import datetime, timezone, timedelta

def run_test():
    print("=== [TEST CHECK 2] MULTI-TOUCH SEQUENCE ENGINE & SCHEDULER ===")
    
    from backend.app.database import SessionLocal
    from backend.app.models.auth_models import User
    from backend.app.models.campaigns import (
        Campaign, CampaignStatus, SequenceStep, EmailTemplate,
        CampaignRecruiter, CampaignRecruiterStatus
    )
    from backend.app.services.send_engine import (
        _advance_recipient_to_next_step, _check_and_finalize_campaign
    )
    from backend.app.services.sequence_scheduler import sequence_scheduler

    db = SessionLocal()
    test_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
    if not test_user:
        test_user = db.query(User).first()
    assert test_user is not None, "No user found in database to associate test campaign"

    test_camp = None
    step1 = None
    step2 = None
    test_cr = None

    try:
        # 1. Create a Test Campaign with 2 Steps
        test_camp = Campaign(
            user_id=test_user.id,
            name="[UNIT_TEST] Multi-Touch Test Campaign",
            status=CampaignStatus.active.value,
            from_name="Test Recruiter",
            from_email="test@talentops.ai"
        )
        db.add(test_camp)
        db.commit()
        db.refresh(test_camp)
        print(f"[PASS] 1. Created test campaign ID={test_camp.campaign_id}")

        tmpl1 = EmailTemplate(campaign_id=test_camp.campaign_id, name="Touch 1", subject="Subject 1", body="Body 1")
        tmpl2 = EmailTemplate(campaign_id=test_camp.campaign_id, name="Touch 2", subject="Subject 2", body="Body 2")
        db.add_all([tmpl1, tmpl2])
        db.commit()
        db.refresh(tmpl1)
        db.refresh(tmpl2)

        step1 = SequenceStep(
            campaign_id=test_camp.campaign_id,
            template_id=tmpl1.template_id,
            step_order=1,
            delay_days=0,
            delay_hours=0,
            is_active=True
        )
        step2 = SequenceStep(
            campaign_id=test_camp.campaign_id,
            template_id=tmpl2.template_id,
            step_order=2,
            delay_days=3,
            delay_hours=2,
            is_active=True
        )
        db.add_all([step1, step2])
        db.commit()
        db.refresh(step1)
        db.refresh(step2)
        print(f"[PASS] 2. Configured multi-touch sequence: Step 1 (Day 0) and Step 2 (Day 3 + 2h delay)")

        # 2. Enroll a test recipient at Step 1
        from backend.app.models.models import Recruiter
        rec = db.query(Recruiter).first()
        rec_id = rec.recruiter_id if rec else 1

        test_cr = CampaignRecruiter(
            campaign_id=test_camp.campaign_id,
            recruiter_id=rec_id,
            current_step_id=step1.step_id,
            status=CampaignRecruiterStatus.delivered.value,
            sent_count=1,
            last_sent_at=datetime.now(timezone.utc)
        )
        db.add(test_cr)
        db.commit()
        db.refresh(test_cr)
        print(f"[PASS] 3. Enrolled recipient {test_cr.campaign_recruiter_id} at Step 1 ({step1.step_id})")

        # 3. Test Step Advancement: Advance from Step 1 to Step 2
        now_before = datetime.now(timezone.utc)
        _advance_recipient_to_next_step(db, test_cr, test_camp.campaign_id)
        db.commit()
        db.refresh(test_cr)

        assert test_cr.current_step_id == step2.step_id, f"Expected step_id {step2.step_id}, got {test_cr.current_step_id}"
        assert test_cr.next_send_at is not None, "next_send_at must be populated after advancing"
        expected_min_send = (now_before.replace(tzinfo=None) if now_before.tzinfo else now_before) + timedelta(days=3, hours=1, minutes=59)
        actual_send_at = test_cr.next_send_at.replace(tzinfo=None) if test_cr.next_send_at.tzinfo else test_cr.next_send_at
        assert actual_send_at >= expected_min_send, f"next_send_at {test_cr.next_send_at} must reflect 3d 2h delay"
        print(f"[PASS] 4. Recipient successfully advanced to Step 2 with scheduled next_send_at={test_cr.next_send_at}")

        # 4. Test Finalization Guard: Campaign should NOT finalize while recipient waits for Step 2
        _check_and_finalize_campaign(test_camp.campaign_id)
        db.refresh(test_camp)
        assert test_camp.status == CampaignStatus.active.value, f"Campaign prematurely closed! Status is {test_camp.status}"
        print("[PASS] 5. Campaign finalization guard verified: campaign remains active while recipients await next step")

        # 5. Test Scheduler Reply Detection Auto-Halt
        test_cr.replied_at = datetime.now(timezone.utc)
        test_cr.next_send_at = datetime.now(timezone.utc) - timedelta(minutes=5) # make it due
        db.commit()

        # Run scheduler sync cycle
        sequence_scheduler._check_due_recipients_sync()
        db.refresh(test_cr)
        assert test_cr.completed_at is not None, "Reply should have marked sequence completed"
        assert test_cr.next_send_at is None, "next_send_at should be cleared on reply"
        print("[PASS] 6. Reply-detection auto-halt verified: sequence stopped, completed_at set, next_send_at cleared")

        # 6. Test Step Advancement Completion: Advance when at last step
        test_cr.current_step_id = step2.step_id
        test_cr.completed_at = None
        _advance_recipient_to_next_step(db, test_cr, test_camp.campaign_id)
        db.commit()
        db.refresh(test_cr)
        assert test_cr.completed_at is not None, "Expected completed_at when no more steps exist"
        print("[PASS] 7. Final step completion verified: completed_at recorded when sequence ends")

        # 7. Test Scheduler stats
        stats = sequence_scheduler.get_stats()
        assert "cycles" in stats and "replies_detected" in stats, f"Invalid stats schema: {stats}"
        print(f"[PASS] 8. SequenceScheduler telemetry verified: stats={stats}")

        print(">>> CHECK 2 PASSED: ALL 8 VERIFICATION ASSERTIONS SUCCEEDED <<<\n")

    finally:
        # Cleanup test records
        try:
            if test_cr:
                db.delete(test_cr)
            if step1:
                db.delete(step1)
            if step2:
                db.delete(step2)
            if test_camp:
                templates = db.query(EmailTemplate).filter(EmailTemplate.campaign_id == test_camp.campaign_id).all()
                for t in templates:
                    db.delete(t)
                db.delete(test_camp)
            db.commit()
        except Exception as cleanup_err:
            print(f"[NOTE] Cleanup note: {cleanup_err}")
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"[FAIL] Check 2 failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
