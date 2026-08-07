"""
Cloud Sync Engine for Microsoft Graph API.
Periodically fetches the Inbox for connected users and maps replies to CampaignRecruiters.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import requests
from sqlalchemy import func

from ..database import SessionLocal
from ..models.auth_models import ConnectedEmailAccount
from ..models.campaigns import Campaign, CampaignRecruiter, CampaignRecruiterStatus, EmailLog, EmailLogStatus
from ..models.models import Recruiter

logger = logging.getLogger(__name__)

def _utcnow():
    return datetime.now(timezone.utc)

def fetch_inbox_messages(access_token: str, last_sync_time: datetime = None) -> list:
    """Fetch latest messages from Graph API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Base URL: Fetch top 50 messages from Inbox, ordered by received date
    url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=50&$orderby=receivedDateTime DESC"
    
    # If we have a last_sync_time, only fetch newer messages
    if last_sync_time:
        # Format as ISO 8601 for Microsoft Graph (e.g. 2023-10-01T12:00:00Z)
        time_str = last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        url += f"&$filter=receivedDateTime ge {time_str}"
        
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("value", [])
        elif resp.status_code == 401:
            logger.warning("Graph API Token expired during sync.")
            return []
        else:
            logger.error(f"Graph API Sync Error: {resp.status_code} - {resp.text}")
            return []
    except Exception as e:
        logger.error(f"Network error during Graph API sync: {e}")
        return []

def process_replies_for_user(user_id: int, access_token: str, last_sync_time: datetime = None) -> datetime:
    """Fetch and process replies for a specific user. Returns the timestamp of the newest processed message."""
    messages = fetch_inbox_messages(access_token, last_sync_time)
    if not messages:
        return last_sync_time
        
    newest_time = last_sync_time
    
    with SessionLocal() as db:
        for msg in messages:
            # Parse received time
            received_str = msg.get("receivedDateTime")
            if received_str:
                try:
                    # '2023-10-01T12:00:00Z' -> datetime object
                    msg_time = datetime.strptime(received_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    if not newest_time or msg_time > newest_time:
                        newest_time = msg_time
                except ValueError:
                    pass

            sender = msg.get("from", {}).get("emailAddress", {}).get("address")
            if not sender:
                continue
                
            sender = sender.lower()
            subject = msg.get("subject", "")
            
            # Find any active or sent CampaignRecruiter matching this sender
            # We look for recruiters the user has emailed.
            # 1. Find recruiters by email
            recruiters = db.query(Recruiter).filter(func.lower(Recruiter.email) == sender).all()
            if not recruiters:
                continue
                
            recruiter_ids = [r.recruiter_id for r in recruiters]
            
            # 2. Find campaigns belonging to this user
            user_campaign_ids = [c.campaign_id for c in db.query(Campaign.campaign_id).filter(Campaign.user_id == user_id).all()]
            if not user_campaign_ids:
                continue
                
            # 3. Find active enrollments
            enrollments = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.recruiter_id.in_(recruiter_ids),
                CampaignRecruiter.campaign_id.in_(user_campaign_ids),
                ~CampaignRecruiter.status.in_([
                    CampaignRecruiterStatus.cancelled.value,
                    CampaignRecruiterStatus.bounced.value,
                    CampaignRecruiterStatus.replied.value
                ])
            ).all()
            
            for cr in enrollments:
                logger.info(f"Marking CampaignRecruiter {cr.campaign_recruiter_id} as REPLIED. Sender: {sender}")
                cr.status = CampaignRecruiterStatus.replied.value
                cr.replied_at = _utcnow()
                
                try:
                    from .mailintel_engine import process_delivery_event
                    process_delivery_event(db, sender, 'replied', cr.campaign_id)
                except Exception as e:
                    logger.error(f"MAILINTEL Reply Error: {e}")
                
                # Check if campaign is terminal
                non_terminal = db.query(CampaignRecruiter).filter(
                    CampaignRecruiter.campaign_id == cr.campaign_id,
                    ~CampaignRecruiter.status.in_([
                        CampaignRecruiterStatus.sent.value,
                        CampaignRecruiterStatus.failed.value,
                        CampaignRecruiterStatus.cancelled.value,
                        CampaignRecruiterStatus.delivered.value,
                        CampaignRecruiterStatus.opened.value,
                        CampaignRecruiterStatus.replied.value,
                        CampaignRecruiterStatus.bounced.value
                    ])
                ).count()
                
                if non_terminal == 0:
                    campaign = db.query(Campaign).filter(Campaign.campaign_id == cr.campaign_id).first()
                    if campaign and campaign.status == "active":
                        campaign.status = "completed"
                    
        db.commit()
        
    return newest_time
    

async def sync_engine_loop():
    """Background daemon to poll Graph API for all connected users."""
    logger.info("Cloud Sync Engine started.")
    from ..routes.bridge import MOCK_OAUTH
    
    while True:
        if MOCK_OAUTH:
            await asyncio.sleep(60)
            continue
            
        try:
            with SessionLocal() as db:
                accounts = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.status == "connected").all()
                for account in accounts:
                    if not account.access_token:
                        continue
                        
                    try:
                        # Process replies
                        newest_time = await asyncio.to_thread(
                            process_replies_for_user, 
                            account.user_id, 
                            account.access_token, 
                            account.last_synced_at
                        )
                        
                        if newest_time and newest_time != account.last_synced_at:
                            # Add a 1-second buffer to avoid missing emails on the exact boundary
                            account.last_synced_at = newest_time + timedelta(seconds=1)
                            db.commit()
                            
                    except Exception as e:
                        logger.error(f"Error syncing account {account.account_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Sync engine supervisor error: {e}")
            
        # Poll every 60 seconds
        await asyncio.sleep(60)
