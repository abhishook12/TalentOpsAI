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
from ..models.campaigns import EmailLog, EmailLogStatus

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

    if not status_record:
        return {"status": "offline", "message": "Bridge not configured", "connected_email": connected_email}
    
    # Removed auto-offline timeout logic to maintain persistent connection
    
    return {
        "status": status_record.status,
        "last_heartbeat": status_record.last_heartbeat.isoformat() if status_record.last_heartbeat else None,
        "uptime_seconds": status_record.uptime_seconds,
        "last_successful_email_at": status_record.last_successful_email_at.isoformat() if status_record.last_successful_email_at else None,
        "consecutive_errors": status_record.consecutive_errors,
        "version": status_record.version,
        "diagnostics_json": status_record.diagnostics_json,
        "connected_email": outlook_account.email_address if outlook_account else None
    }


@router.get("/tasks")
def get_bridge_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Fetch pending emails for the bridge."""
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
from ..models.campaigns import EmailLog, EmailLogStatus, CampaignRecruiter, CampaignRecruiterStatus
from datetime import datetime

def _utcnow():
    return datetime.utcnow()

@router.post("/results")
def post_bridge_results(payload: BridgeResultsPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Receive results from the bridge."""
    campaign_ids_to_check = set()
    for res in payload.results:
        log = db.query(EmailLog).filter(EmailLog.user_id == current_user.id, EmailLog.log_id == res.log_id).first()
        if log:
            campaign_ids_to_check.add(log.campaign_id)
            log.body_html = None  # Free the full-body payload once terminal (Supabase 500MB free tier)
            recipient = db.query(CampaignRecruiter).filter(CampaignRecruiter.user_id == current_user.id, CampaignRecruiter.campaign_recruiter_id == log.campaign_recruiter_id).first()
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
    
    from ..models.campaigns import Campaign, CampaignStatus
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

@router.get('/oauth/login')
def bridge_oauth_login(redirect_uri: str = '/profile?bridge=connected', popup: str = 'false', current_user: User = Depends(get_current_user_from_request)):
    # Placeholder OAuth redirect to Microsoft login
    # In a real app, this would redirect to https://login.microsoftonline.com/... 
    return RedirectResponse(url=f'/api/bridge/oauth/callback?user_id={current_user.id}&redirect_uri={urllib.parse.quote(redirect_uri)}&popup={popup}')

@router.get('/oauth/callback')
def bridge_oauth_callback(user_id: int, redirect_uri: str = '/profile?bridge=connected', popup: str = 'false', db: Session = Depends(get_db)):
    status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == user_id).first()
    if not status_record:
        status_record = UserBridgeStatus(user_id=user_id)
        db.add(status_record)
    
    status_record.status = 'online'
    status_record.last_heartbeat = _utcnow()
    db.commit()
    
    if popup == 'true':
        return HTMLResponse(content="<html><script>window.close();</script><body style='font-family:sans-serif;text-align:center;padding:50px;'><h2>Connection Successful!</h2><p>This window will close automatically.</p></body></html>")
        
    # Redirect back to frontend profile
    return RedirectResponse(url=redirect_uri)

@router.post('/disconnect')
def bridge_disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
    if status_record:
        status_record.status = 'offline'
        db.commit()
    return {'status': 'ok'}
