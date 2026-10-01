"""
Sequence Scheduler - Background task for multi-touch email sequences.
Checks every 60 seconds for recipients whose next_send_at has passed,
then triggers sending of their next sequence step.
Auto-stops sequences on reply detection.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("sequence_scheduler")

class SequenceScheduler:
    def __init__(self):
        self._running = False
        self._task = None
        self._check_interval = 60  # seconds
        self._stats = {"cycles": 0, "recipients_processed": 0, "replies_detected": 0, "steps_triggered": 0}
    
    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[SEQUENCE_SCHEDULER] Started")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[SEQUENCE_SCHEDULER] Stopped")
    
    async def _run_loop(self):
        while self._running:
            try:
                await self._check_due_recipients()
                self._stats["cycles"] += 1
            except Exception as e:
                logger.error(f"[SEQUENCE_SCHEDULER] Error in check cycle: {e}")
            await asyncio.sleep(self._check_interval)
    
    async def _check_due_recipients(self):
        await asyncio.to_thread(self._check_due_recipients_sync)
    
    def _check_due_recipients_sync(self):
        from ..database import SessionLocal
        from ..models.campaigns import (
            Campaign, CampaignStatus, CampaignRecruiter, 
            CampaignRecruiterStatus, SequenceStep
        )
        
        now = datetime.now(timezone.utc)
        
        with SessionLocal() as db:
            # Find recipients due for next step
            due_recipients = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.next_send_at <= now,
                CampaignRecruiter.next_send_at.isnot(None),
                CampaignRecruiter.completed_at.is_(None),
                CampaignRecruiter.status.in_([
                    CampaignRecruiterStatus.delivered.value,
                    'Delivered', 'delivered'
                ])
            ).limit(100).all()
            
            if not due_recipients:
                return
            
            logger.info(f"[SEQUENCE_SCHEDULER] Found {len(due_recipients)} recipients due for next step")
            
            # Group by campaign
            campaigns_to_process = {}
            for cr in due_recipients:
                # Reply detection: auto-stop if recipient replied
                if cr.replied_at:
                    cr.completed_at = now
                    cr.next_send_at = None
                    self._stats["replies_detected"] += 1
                    logger.info(f"[SEQUENCE_SCHEDULER] Reply detected for recipient {cr.campaign_recruiter_id}, stopping sequence")
                    continue
                
                # Verify campaign is still active
                if cr.campaign_id not in campaigns_to_process:
                    campaign = db.query(Campaign).filter(
                        Campaign.campaign_id == cr.campaign_id
                    ).first()
                    if not campaign or campaign.status not in (CampaignStatus.active.value, 'active'):
                        continue
                    campaigns_to_process[cr.campaign_id] = campaign
                
                # Mark as pending so the send engine picks it up
                cr.status = CampaignRecruiterStatus.pending.value
                cr.next_send_at = None  # Clear so it doesn't get picked up again
                self._stats["steps_triggered"] += 1
                self._stats["recipients_processed"] += 1
            
            db.commit()
        
        # Trigger campaign processing for each campaign with due recipients
        for campaign_id in campaigns_to_process:
            try:
                asyncio.get_event_loop().create_task(self._trigger_campaign_send(campaign_id))
            except Exception as e:
                logger.error(f"[SEQUENCE_SCHEDULER] Failed to trigger campaign {campaign_id}: {e}")
    
    async def _trigger_campaign_send(self, campaign_id: int):
        from .send_engine import start_campaign
        try:
            await start_campaign(campaign_id)
        except Exception as e:
            logger.error(f"[SEQUENCE_SCHEDULER] Error starting campaign {campaign_id}: {e}")
    
    def auto_enroll_recruiter(
        self,
        db,
        recruiter_id: int,
        email: str,
        name: str = "",
        company: str = "",
        title: str = "",
        confidence: int = 80,
        source: str = "web_intelligence",
    ) -> List[int]:
        """
        Pillar 5 Closed-Loop Autonomous Flywheel:
        Automatically enrolls newly discovered and promoted recruiters into active campaigns
        that have auto-enrollment enabled in metadata.
        """
        import json
        from ..models.campaigns import (
            Campaign, CampaignStatus, CampaignRecruiter,
            CampaignRecruiterStatus, SequenceStep
        )

        if not email or "@" not in email:
            return []

        active_campaigns = db.query(Campaign).filter(
            Campaign.is_active == True,
            Campaign.is_archived == False,
            Campaign.status.in_([CampaignStatus.active.value, 'active'])
        ).all()

        enrolled_campaign_ids = []
        now = datetime.now(timezone.utc)

        for camp in active_campaigns:
            meta = {}
            if camp.metadata_json:
                try:
                    meta = json.loads(camp.metadata_json)
                except Exception:
                    meta = {}

            if not meta.get("auto_enroll"):
                continue

            min_conf = meta.get("min_confidence", 70)
            if confidence < min_conf:
                continue

            existing = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.campaign_id == camp.campaign_id,
                CampaignRecruiter.recruiter_id == recruiter_id
            ).first()
            if existing:
                continue

            first_step = db.query(SequenceStep).filter(
                SequenceStep.campaign_id == camp.campaign_id,
                SequenceStep.is_active == True
            ).order_by(SequenceStep.step_order.asc()).first()

            first_name = name.split()[0] if name else "there"
            variables = {
                "first_name": first_name,
                "full_name": name,
                "company": company or "",
                "title": title or "",
                "email": email
            }

            cr = CampaignRecruiter(
                campaign_id=camp.campaign_id,
                recruiter_id=recruiter_id,
                current_step_id=first_step.step_id if first_step else None,
                status=CampaignRecruiterStatus.pending.value,
                enrolled_at=now,
                next_send_at=now,
                variables_json=json.dumps(variables),
                metadata_json=json.dumps({
                    "auto_enrolled": True,
                    "source": source,
                    "confidence": confidence,
                    "enrolled_timestamp": now.isoformat()
                })
            )
            db.add(cr)
            enrolled_campaign_ids.append(camp.campaign_id)

        if enrolled_campaign_ids:
            try:
                db.flush()
                logger.info(
                    "[SEQUENCE_SCHEDULER] Auto-enrolled recruiter #%d (%s) into campaigns %s",
                    recruiter_id, email, enrolled_campaign_ids
                )
                self._stats["recipients_processed"] += len(enrolled_campaign_ids)
            except Exception as e:
                logger.error("[SEQUENCE_SCHEDULER] Failed to flush auto-enrollment: %s", e)

        return enrolled_campaign_ids

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "check_interval_seconds": self._check_interval,
            **self._stats
        }

# Singleton
sequence_scheduler = SequenceScheduler()

def auto_enroll_recruiter(
    db,
    recruiter_id: int,
    email: str,
    name: str = "",
    company: str = "",
    title: str = "",
    confidence: int = 80,
    source: str = "web_intelligence",
) -> List[int]:
    """Convenience module function delegating to singleton."""
    return sequence_scheduler.auto_enroll_recruiter(
        db=db,
        recruiter_id=recruiter_id,
        email=email,
        name=name,
        company=company,
        title=title,
        confidence=confidence,
        source=source,
    )
