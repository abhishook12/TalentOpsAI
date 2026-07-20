with open('app/routes/bridge.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Add imports for UserBridgeStatus and User
if 'UserBridgeStatus' not in content:
    content = content.replace('from ..models.campaigns import EmailLog', 'from ..models.auth_models import User, UserBridgeStatus\nfrom ..services.auth_service import get_current_user_from_request\nfrom ..models.campaigns import EmailLog')

# Replace heartbeat function
new_heartbeat = '''
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
    if not status_record:
        return {"status": "offline", "message": "Bridge not configured"}
    
    # Check if offline based on heartbeat
    is_offline = False
    if status_record.last_heartbeat:
        time_diff = (_utcnow() - status_record.last_heartbeat).total_seconds()
        if time_diff > 30:
            is_offline = True
            
    if is_offline and status_record.status == "online":
        status_record.status = "offline"
        db.commit()
        
    return {
        "status": status_record.status,
        "last_heartbeat": status_record.last_heartbeat.isoformat() if status_record.last_heartbeat else None,
        "uptime_seconds": status_record.uptime_seconds,
        "last_successful_email_at": status_record.last_successful_email_at.isoformat() if status_record.last_successful_email_at else None,
        "consecutive_errors": status_record.consecutive_errors,
        "version": status_record.version,
        "diagnostics_json": status_record.diagnostics_json
    }
'''

content = re.sub(r'HEARTBEAT_FILE =.*?return \{"status\": \"error\", \"detail\": str\(e\)\}', new_heartbeat, content, flags=re.DOTALL)

# Add auth to get_bridge_tasks
content = re.sub(r'def get_bridge_tasks\(db: Session = Depends\(get_db\)\):', 'def get_bridge_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):', content)

# Filter tasks by user_id
content = content.replace('EmailLog.status == EmailLogStatus.sending.value,', 'EmailLog.user_id == current_user.id, EmailLog.status == EmailLogStatus.sending.value,')

# Add auth to post_bridge_results
content = re.sub(r'def post_bridge_results\(payload: BridgeResultsPayload, db: Session = Depends\(get_db\)\):', 'def post_bridge_results(payload: BridgeResultsPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):', content)

success_update = '''
                if recipient:
                    recipient.status = CampaignRecruiterStatus.sent.value
                    recipient.last_sent_at = _utcnow()
                    recipient.sent_count += 1
                
                # Update bridge status
                status_record = db.query(UserBridgeStatus).filter(UserBridgeStatus.user_id == current_user.id).first()
                if status_record:
                    status_record.last_successful_email_at = _utcnow()
                    status_record.consecutive_errors = 0
'''
content = content.replace('''
                if recipient:
                    recipient.status = CampaignRecruiterStatus.sent.value
                    recipient.last_sent_at = _utcnow()
                    recipient.sent_count += 1
''', success_update)

content = content.replace('db.query(EmailLog).filter(EmailLog.log_id == res.log_id)', 'db.query(EmailLog).filter(EmailLog.user_id == current_user.id, EmailLog.log_id == res.log_id)')
content = content.replace('db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == log.campaign_recruiter_id)', 'db.query(CampaignRecruiter).filter(CampaignRecruiter.user_id == current_user.id, CampaignRecruiter.campaign_recruiter_id == log.campaign_recruiter_id)')
content = content.replace('campaign = db.query(Campaign).filter(Campaign.campaign_id == cid).first()', 'campaign = db.query(Campaign).filter(Campaign.user_id == current_user.id, Campaign.campaign_id == cid).first()')

with open('app/routes/bridge.py', 'w', encoding='utf-8') as f:
    f.write(content)
