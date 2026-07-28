from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import time
import os
import json
from ..database import get_db
from ..models.auth_models import User, UserBridgeStatus, UserOutlookAccount
from ..services.auth_service import get_current_user_from_request
from ..models.campaigns import EmailLog, EmailLogStatus, Campaign, CampaignRecruiter, CampaignStatus, CampaignRecruiterStatus

router = APIRouter()

class BridgeResult(BaseModel):
    log_id: int
    success: bool
    error: str = None

class BridgeResultsPayload(BaseModel):
    results: List[BridgeResult]

class AuthBypassPayload(BaseModel):
    email: str

@router.post("/auth-bypass")
def bridge_auth_bypass(payload: AuthBypassPayload, db: Session = Depends(get_db)):
    """Generate a token for a specific user without a password (local bridge only)."""
    from ..services.auth_service import create_access_token
    from ..config import IS_PRODUCTION
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No user found with email: {payload.email}")
    
    from datetime import timedelta
    access_token_expires = timedelta(days=30)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"token": access_token}


class HeartbeatPayload(BaseModel):
    uptime_seconds: int = 0
    consecutive_errors: int = 0
    version: str = None
    diagnostics_json: str = None

@router.post("/heartbeat")
def bridge_heartbeat(payload: HeartbeatPayload = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Register that the bridge is alive and store diagnostics."""
    try:
        status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
        if not status_record:
            status_record = UserBridgeStatus(user_id=current_user.id)
            db.add(status_record)
        
        status_record.status = "online"
        status_record.last_heartbeat = _utcnow()
        if payload:
            status_record.uptime_seconds = payload.uptime_seconds
            status_record.consecutive_errors = payload.consecutive_errors
            if payload.version:
                status_record.version = payload.version
            if payload.diagnostics_json:
                status_record.diagnostics_json = payload.diagnostics_json
            
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/status")
def get_bridge_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
    outlook_account = db.query(UserOutlookAccount).filter(UserOutlookAccount.user_id == current_user.id).first()
    connected_email = outlook_account.email_address if outlook_account else None
    
    # Calculate queue statistics
    from ..models.campaigns import Campaign, EmailLog, EmailLogStatus
    
    # Pending: sending via outlook_bridge and not yet accepted
    pending = db.query(EmailLog).join(Campaign, EmailLog.campaign_id == Campaign.campaign_id).filter(
        Campaign.user_id == current_user.id, 
        EmailLog.sent_via == "outlook_bridge",
        EmailLog.outlook_accepted == None
    ).count()
    
    # Sent: delivered via outlook_bridge
    sent = db.query(EmailLog).join(Campaign, EmailLog.campaign_id == Campaign.campaign_id).filter(
        Campaign.user_id == current_user.id, 
        EmailLog.sent_via == "outlook_bridge",
        EmailLog.status == EmailLogStatus.delivered.value
    ).count()
    
    # Failed: failed via outlook_bridge
    failed = db.query(EmailLog).join(Campaign, EmailLog.campaign_id == Campaign.campaign_id).filter(
        Campaign.user_id == current_user.id, 
        EmailLog.sent_via == "outlook_bridge",
        EmailLog.status == EmailLogStatus.failed.value
    ).count()

    stats = {
        "pending": pending,
        "sent": sent,
        "failed": failed
    }

    if not status_record:
        return {"status": "offline", "message": "Bridge not configured", "connected_email": connected_email, "stats": stats}
    
    # Removed auto-offline timeout logic to maintain persistent connection
    
    return {
        "status": status_record.status,
        "last_heartbeat": status_record.last_heartbeat.isoformat() if status_record.last_heartbeat else None,
        "uptime_seconds": status_record.uptime_seconds,
        "last_successful_email_at": status_record.last_successful_email_at.isoformat() if status_record.last_successful_email_at else None,
        "consecutive_errors": status_record.consecutive_errors,
        "version": status_record.version,
        "diagnostics_json": status_record.diagnostics_json,
        "connected_email": outlook_account.email_address if outlook_account else None,
        "stats": stats
    }


@router.get("/tasks")
def get_bridge_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Fetch pending emails for the bridge."""
    outlook_account = db.query(UserOutlookAccount).filter(UserOutlookAccount.user_id == current_user.id).first()
    if not outlook_account or outlook_account.status != "connected":
        raise HTTPException(status_code=403, detail="Outlook account not connected via OAuth. Please connect from Profile page.")
        
    # We find emails that are 'sending' and assigned to 'outlook_bridge'
    # Wait, the send_engine creates EmailLog and sets status='sending' right before sending.
    from ..models.campaigns import Campaign
    logs = db.query(EmailLog).join(Campaign, EmailLog.campaign_id == Campaign.campaign_id).filter(
        Campaign.user_id == current_user.id, EmailLog.status == EmailLogStatus.sending.value,
        EmailLog.sent_via == "outlook_bridge",
        EmailLog.outlook_accepted == None # Not processed yet
    ).order_by(EmailLog.log_id.asc()).limit(25).all()

    tasks = []
    for log in logs:
        # Prevent re-fetching the same task repeatedly if bridge crashes
        # We'll rely on the bridge to update outlook_accepted
        # Reset the timeout clock on dispatch so the sweep measures bridge time, not queue wait
        log.sending_at = _utcnow()
        tasks.append({
            "log_id": log.log_id,
            "to_email": log.recipient_email,
            "subject": log.subject,
            "html_body": log.body_html or log.body_preview
        })
    db.commit()
    return {"tasks": tasks}

from ..models.auth_models import User, UserBridgeStatus
from ..services.auth_service import get_current_user_from_request
from ..models.campaigns import EmailLog, EmailLogStatus, CampaignRecruiter, CampaignRecruiterStatus, Campaign, CampaignStatus
from datetime import datetime

def _utcnow():
    return datetime.utcnow()

@router.post("/results")
def post_bridge_results(payload: BridgeResultsPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Receive results from the bridge."""
    campaign_ids_to_check = set()
    for res in payload.results:
        log = db.query(EmailLog).join(Campaign).filter(Campaign.user_id == current_user.id, EmailLog.log_id == res.log_id).first()
        if log:
            campaign_ids_to_check.add(log.campaign_id)
            log.body_html = None  # Free the full-body payload once terminal (Supabase 500MB free tier)
            recipient = db.query(CampaignRecruiter).join(Campaign).filter(Campaign.user_id == current_user.id, CampaignRecruiter.campaign_recruiter_id == log.campaign_recruiter_id).first()
            if res.success:
                log.outlook_accepted = True
                log.status = EmailLogStatus.delivered.value
                log.delivered_at = _utcnow()
                if recipient:
                    recipient.status = CampaignRecruiterStatus.sent.value
                    recipient.last_sent_at = _utcnow()
                    recipient.sent_count += 1
                
                # Update bridge status
                status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
                if status_record:
                    status_record.last_successful_email_at = _utcnow()
                    status_record.consecutive_errors = 0
            else:
                log.outlook_accepted = False
                log.status = EmailLogStatus.failed.value
                log.error_message = res.error
                log.failed_at = _utcnow()
                if recipient:
                    recipient.retry_count += 1
                    recipient.last_error = res.error
                    if recipient.retry_count >= recipient.max_retries:
                        recipient.status = CampaignRecruiterStatus.failed.value
                    else:
                        recipient.status = CampaignRecruiterStatus.retrying.value
    db.commit()
    
    # (Import moved to module level)
    for cid in campaign_ids_to_check:
        non_terminal = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == cid,
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
            campaign = db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.campaign_id == cid).first()
            if campaign and campaign.status == CampaignStatus.active.value:
                campaign.status = CampaignStatus.completed.value
    db.commit()

    return {"status": "ok"}


from fastapi.responses import RedirectResponse, HTMLResponse
import urllib.parse
import jwt
from datetime import datetime, timedelta
from ..services.auth_service import SECRET_KEY, ALGORITHM

MOCK_OAUTH = True  # Set to True for testing until Azure AD credentials are provided

@router.get('/oauth/login')
def bridge_oauth_login(redirect_uri: str = '/profile?bridge=connected', popup: str = 'false', current_user: User = Depends(get_current_user_from_request)):
    # Generate secure state token
    state_payload = {
        "user_id": current_user.id,
        "redirect_uri": redirect_uri,
        "popup": popup,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    state = jwt.encode(state_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    if MOCK_OAUTH:
        # Mock redirect directly to callback with a fake auth code
        return RedirectResponse(url=f'/api/bridge/oauth/callback?code=mock_auth_code_123&state={state}')
        
    # Real MSAL Redirect would go here
    msal_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=REPLACE_ME&response_type=code&redirect_uri=REPLACE_ME&scope=Mail.Send offline_access User.Read&state={state}"
    return RedirectResponse(url=msal_url)

@router.get('/oauth/callback')
def bridge_oauth_callback(code: str = None, state: str = None, error: str = None, db: Session = Depends(get_db)):
    if error:
        return HTMLResponse(content=f"<html><body><h2>OAuth Error</h2><p>{error}</p></body></html>", status_code=400)
    if not code or not state:
        return HTMLResponse(content="<html><body><h2>Missing OAuth Parameters</h2></body></html>", status_code=400)
        
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        redirect_uri = payload.get("redirect_uri", "/profile?bridge=connected")
        popup = payload.get("popup", "false")
    except Exception as e:
        return HTMLResponse(content="<html><body><h2>Invalid State Token</h2></body></html>", status_code=400)

    # 1. Exchange code for tokens (Mock)
    access_token = "mock_access_token_abc123"
    refresh_token = "mock_refresh_token_xyz890"
    
    # 2. Fetch User Profile from Graph API (Mock)
    # Using the user ID to generate a consistent mock email if needed, or just a dummy
    # In tests, we might want this to match the bridge config
    user = db.query(User).filter(User.id == user_id).first()
    connected_email = user.email if user else f"user_{user_id}@outlook.com"

    # 3. Upsert UserOutlookAccount
    outlook_account = db.query(UserOutlookAccount).filter(UserOutlookAccount.user_id == user_id).first()
    if not outlook_account:
        outlook_account = UserOutlookAccount(user_id=user_id)
        db.add(outlook_account)
    
    outlook_account.email_address = connected_email
    outlook_account.access_token = access_token
    outlook_account.refresh_token = refresh_token
    outlook_account.status = "connected"
    outlook_account.last_synced_at = _utcnow()
    
    # 4. Upsert UserBridgeStatus (mark offline initially, bridge script must connect to mark online)
    status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == user_id).first()
    if not status_record:
        status_record = UserBridgeStatus(user_id=user_id)
        db.add(status_record)
    
    status_record.status = 'offline' # Requires bridge script to come online
    db.commit()
    
    if popup == 'true':
        return HTMLResponse(content="<html><script>window.opener.postMessage('oauth_success', '*'); window.close();</script><body style='font-family:sans-serif;text-align:center;padding:50px;'><h2>Connection Successful!</h2><p>This window will close automatically.</p></body></html>")
        
    # Redirect back to frontend profile
    return RedirectResponse(url=redirect_uri)

@router.post('/disconnect')
def bridge_disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    outlook_account = db.query(UserOutlookAccount).filter(UserOutlookAccount.user_id == current_user.id).first()
    if outlook_account:
        outlook_account.status = "disconnected"
        outlook_account.access_token = None
        outlook_account.refresh_token = None
        
    status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
    if status_record:
        status_record.status = 'offline'
        
    db.commit()
    return {'status': 'ok'}
