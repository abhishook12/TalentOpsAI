import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import os
import smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.campaigns import (
    Campaign,
    CampaignRecruiter,
    CampaignRecruiterStatus,
    CampaignStatus,
    EmailTemplate,
    SequenceStep,
    EmailSignature,
    ensure_campaign_tables,
)
from ..models.models import Recruiter

router = APIRouter()

class BulkSendRequest(BaseModel):
    emails: list[str]
    subject: str
    body: str
    from_email: str
    cc: Optional[str] = None
    bcc: Optional[str] = None

def send_bulk_emails_background(request: BulkSendRequest):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    if not smtp_user or not smtp_pass:
        print("❌ Cannot send bulk emails: SMTP_USER or SMTP_PASS not set.")
        return

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        
        for email_addr in request.emails:
            msg = EmailMessage()
            msg.set_content(request.body)
            msg["Subject"] = request.subject
            msg["From"] = f"TalentOps <{request.from_email}>"
            msg["To"] = email_addr
            
            if request.cc:
                msg["Cc"] = request.cc
            if request.bcc:
                msg["Bcc"] = request.bcc
                
            try:
                server.send_message(msg)
                print(f"✅ Sent email to {email_addr}")
            except Exception as e:
                print(f"❌ Failed to send to {email_addr}: {e}")
                
        server.quit()
        print("✅ Bulk send background task completed.")
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")

@router.post("/bulk-send")
def bulk_send_emails(request: BulkSendRequest, background_tasks: BackgroundTasks):
    if not request.emails:
        raise HTTPException(status_code=400, detail="No recipients provided.")
    
    background_tasks.add_task(send_bulk_emails_background, request)
    return {"status": "queued", "count": len(request.emails)}


class ValidateRecipientsRequest(BaseModel):
    emails: list[str]

@router.post("/validate-recipients")
def validate_recipients_endpoint(payload: ValidateRecipientsRequest, db: Session = Depends(get_db)):
    from ..services.recipient_validator import validate_recipients
    from dataclasses import asdict
    result = validate_recipients(payload.emails, db)
    return asdict(result)

@router.post("/{campaign_id}/start")
async def api_start_campaign(campaign_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from ..services.send_engine import start_campaign
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    background_tasks.add_task(start_campaign, campaign_id)
    return {"status": "started", "campaign_id": campaign_id}

@router.post("/{campaign_id}/pause")
def api_pause_campaign(campaign_id: int, db: Session = Depends(get_db)):
    from ..services.send_engine import pause_campaign
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    pause_campaign(campaign_id)
    return {"status": "paused", "campaign_id": campaign_id}

@router.post("/{campaign_id}/resume")
async def api_resume_campaign(campaign_id: int, db: Session = Depends(get_db)):
    from ..services.send_engine import resume_campaign
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await resume_campaign(campaign_id)
    return {"status": "resumed", "campaign_id": campaign_id}

@router.post("/{campaign_id}/cancel")
def api_cancel_campaign(campaign_id: int, db: Session = Depends(get_db)):
    from ..services.send_engine import cancel_campaign
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    cancel_campaign(campaign_id)
    return {"status": "cancelled", "campaign_id": campaign_id}

class PreviewRequest(BaseModel):
    recruiter_id: int
    subject_template: str
    body_template: str
    signature_id: Optional[int] = None

@router.post("/{campaign_id}/preview")
def api_preview_email(campaign_id: int, request: PreviewRequest, db: Session = Depends(get_db)):
    from ..services.personalization import preview_email
    
    recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == request.recruiter_id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    company = recruiter.company if hasattr(recruiter, 'company') else None
    
    signature_html = None
    if request.signature_id:
        sig = db.query(EmailSignature).filter(EmailSignature.signature_id == request.signature_id).first()
        if sig:
            signature_html = sig.html_content
            
    preview = preview_email(request.subject_template, request.body_template, recruiter, company, signature_html)
    return preview

@router.post("/{campaign_id}/validate-before-send")
def api_validate_before_send(campaign_id: int, db: Session = Depends(get_db)):
    from ..services.send_engine import _check_bridge_health
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    healthy, error = _check_bridge_health()
    
    # Check if there are active sequence steps with templates
    has_template = False
    for step in campaign.sequence_steps:
        if step.is_active and step.template_id:
            has_template = True
            break
            
    # Check if there are enrolled recipients
    has_recipients = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == campaign_id).count() > 0
    
    return {
        "bridge_healthy": healthy,
        "bridge_error": error if not healthy else None,
        "has_template": has_template,
        "has_recipients": has_recipients,
        "ready": healthy and has_template and has_recipients
    }

class SignatureCreate(BaseModel):
    name: str
    html_content: str
    is_default: bool = False
    
class SignatureUpdate(BaseModel):
    name: Optional[str] = None
    html_content: Optional[str] = None
    is_default: Optional[bool] = None

@router.get("/signatures/list")
def list_signatures(db: Session = Depends(get_db)):
    sigs = db.query(EmailSignature).order_by(EmailSignature.created_at.desc()).all()
    return [{
        "signature_id": s.signature_id,
        "name": s.name,
        "html_content": s.html_content,
        "is_default": s.is_default,
        "created_at": s.created_at.isoformat()
    } for s in sigs]

@router.post("/signatures/create")
def create_signature(req: SignatureCreate, db: Session = Depends(get_db)):
    # Simple hardcoded user for now
    user_email = "abhishekjadon824@gmail.com"
    
    if req.is_default:
        db.query(EmailSignature).filter(EmailSignature.user_email == user_email).update({"is_default": False})
        
    sig = EmailSignature(
        user_email=user_email,
        name=req.name,
        html_content=req.html_content,
        is_default=req.is_default
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return {"status": "success", "signature_id": sig.signature_id}

@router.put("/signatures/{signature_id}")
def update_signature(signature_id: int, req: SignatureUpdate, db: Session = Depends(get_db)):
    sig = db.query(EmailSignature).filter(EmailSignature.signature_id == signature_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
        
    if req.is_default:
        db.query(EmailSignature).filter(EmailSignature.user_email == sig.user_email).update({"is_default": False})
        
    if req.name is not None:
        sig.name = req.name
    if req.html_content is not None:
        sig.html_content = req.html_content
    if req.is_default is not None:
        sig.is_default = req.is_default
        
    db.commit()
    return {"status": "success"}

@router.delete("/signatures/{signature_id}")
def delete_signature(signature_id: int, db: Session = Depends(get_db)):
    sig = db.query(EmailSignature).filter(EmailSignature.signature_id == signature_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    # Nullify references in campaigns
    db.query(Campaign).filter(Campaign.signature_id == signature_id).update({"signature_id": None})
    
    db.delete(sig)
    db.commit()
    return {"status": "success"}


class EnrollEmailsRequest(BaseModel):
    emails: list[str]

@router.post("/{campaign_id}/enroll-emails")
def enroll_emails(campaign_id: int, payload: EnrollEmailsRequest, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    first_step = db.query(SequenceStep).filter(SequenceStep.campaign_id == campaign_id).order_by(SequenceStep.step_order.asc()).first()
    if not first_step:
        raise HTTPException(status_code=400, detail="Campaign must have at least one sequence step")

    enrolled = 0
    try:
        for email in payload.emails:
            clean_email = email.strip().lower()
            if not clean_email:
                continue
                
            # Find or create recruiter
            rec = db.query(Recruiter).filter(func.lower(Recruiter.email) == clean_email).first()
            if not rec:
                rec = Recruiter(
                    email=clean_email,
                    recruiter_name=clean_email.split('@')[0], # Fallback name
                    data_source="campaign_import"
                )
                db.add(rec)
                db.flush() # Flush instead of commit to get the ID within the transaction
                
            # Check if already enrolled
            existing = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.campaign_id == campaign_id,
                CampaignRecruiter.recruiter_id == rec.recruiter_id
            ).first()
            
            if not existing:
                cr = CampaignRecruiter(
                    campaign_id=campaign_id,
                    recruiter_id=rec.recruiter_id,
                    current_step_id=first_step.step_id,
                    status=CampaignRecruiterStatus.pending.value,
                    enrolled_at=utcnow(),
                    next_send_at=campaign.start_at or utcnow()
                )
                db.add(cr)
                enrolled += 1
                
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to enroll emails: {str(e)}")
        
    return {"enrolled_count": enrolled}

@router.get("/{campaign_id}/progress")
async def stream_campaign_progress(campaign_id: int):
    # Removed Depends(get_db) to prevent holding a DB connection for the duration of the stream
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    
    def _snapshot(last_log_id: int):
        # Runs in a worker thread: blocking DB calls must never run on the event loop
        # (they stall every other request on the single Render instance).
        from ..database import SessionLocal
        from ..models.campaigns import EmailLog
        from sqlalchemy import func as sa_func

        with SessionLocal() as s_db:
            camp_status = s_db.query(Campaign.status).filter(Campaign.campaign_id == campaign_id).scalar()
            if camp_status is None:
                return None, last_log_id

            # One GROUP BY replaces seven separate COUNT queries
            counts = dict(
                s_db.query(CampaignRecruiter.status, sa_func.count())
                .filter(CampaignRecruiter.campaign_id == campaign_id)
                .group_by(CampaignRecruiter.status)
                .all()
            )
            total = sum(counts.values())
            terminal_states = ['Sent', 'Delivered', 'Opened', 'Replied', 'Bounced', 'Cancelled']
            sent = sum(counts.get(s, 0) for s in terminal_states)
            failed = counts.get('Failed', 0)
            queued = counts.get('Queued', 0)
            sending = counts.get('Sending', 0)
            retrying = counts.get('Retrying', 0)
            pending = counts.get('Pending', 0) + queued + sending + retrying

            new_logs = (
                s_db.query(
                    EmailLog.log_id, EmailLog.recipient_email, EmailLog.status,
                    EmailLog.sending_at, EmailLog.error_message
                )
                .filter(EmailLog.campaign_id == campaign_id, EmailLog.log_id > last_log_id)
                .order_by(EmailLog.log_id.asc())
                .limit(100)
                .all()
            )

            logs_data = []
            for log in new_logs:
                logs_data.append({
                    "log_id": log.log_id,
                    "email": log.recipient_email,
                    "status": log.status,
                    "time": log.sending_at.isoformat() if log.sending_at else None,
                    "error": log.error_message
                })
                last_log_id = max(last_log_id, log.log_id)

            data = {
                "status": camp_status,
                "total": total,
                "sent": sent,
                "failed": failed,
                "pending": pending,
                "queued": queued,
                "sending": sending,
                "retrying": retrying,
                "progress_percent": round((sent / total) * 100, 1) if total > 0 else 0,
                "new_logs": logs_data
            }
            return data, last_log_id

    async def event_generator():
        # Keep track of what we've already sent to avoid redundant data
        last_log_id = 0
        first_sent = None  # (monotonic_time, sent_count) baseline for observed rate

        while True:
            data, last_log_id = await asyncio.to_thread(_snapshot, last_log_id)
            if data is None:
                break

            # Observed throughput → ETA (replaces the hardcoded estimate the UI expects)
            now = time.monotonic()
            if first_sent is None or data["sent"] < first_sent[1]:
                first_sent = (now, data["sent"])
            elapsed = now - first_sent[0]
            delta = data["sent"] - first_sent[1]
            rate = (delta / elapsed) if elapsed > 2 and delta > 0 else 0
            remaining = data["pending"]
            data["rate_per_minute"] = int(rate * 60)
            data["eta_seconds"] = int(remaining / rate) if rate > 0 else 0

            yield f"data: {json.dumps(data)}\n\n"

            if data["status"] in ['completed', 'failed', 'cancelled']:
                # One final status, then close
                break

            await asyncio.sleep(2)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/{campaign_id}/delivery-logs")
def get_campaign_delivery_logs(campaign_id: int, db: Session = Depends(get_db)):
    """Fetch detailed delivery logs for the campaign."""
    from ..models.campaigns import EmailLog, CampaignRecruiter
    from sqlalchemy.orm import joinedload
    
    logs = (
        db.query(EmailLog)
        .filter(EmailLog.campaign_id == campaign_id)
        .order_by(EmailLog.log_id.desc())
        .options(joinedload(EmailLog.campaign_recruiter))
        .all()
    )
    
    res = []
    for log in logs:
        cr = log.campaign_recruiter
        res.append({
            "id": log.log_id,
            "email": log.recipient_email,
            "status": log.status,
            "last_sent": log.sending_at.isoformat() if log.sending_at else None,
            "error": log.error_message,
            "retry_count": cr.retry_count if cr else 0
        })
    return {"items": res}

VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_json_text(value: Optional[dict[str, Any] | list[Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def from_json_text(value: Optional[str], fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def extract_variables(subject: str, body: str) -> list[str]:
    found = set(VARIABLE_PATTERN.findall(subject or "") + VARIABLE_PATTERN.findall(body or ""))
    return sorted(found)


def serialize_template(template: EmailTemplate) -> dict[str, Any]:
    return {
        "template_id": template.template_id,
        "campaign_id": template.campaign_id,
        "name": template.name,
        "subject": template.subject,
        "body": template.body,
        "variables": from_json_text(template.variables_json, []),
        "is_active": template.is_active,
        "created_at": str(template.created_at) if template.created_at else None,
        "updated_at": str(template.updated_at) if template.updated_at else None,
    }


def serialize_sequence_step(step: SequenceStep) -> dict[str, Any]:
    return {
        "step_id": step.step_id,
        "campaign_id": step.campaign_id,
        "template_id": step.template_id,
        "step_order": step.step_order,
        "delay_days": step.delay_days,
        "delay_hours": step.delay_hours,
        "is_active": step.is_active,
        "created_at": str(step.created_at) if step.created_at else None,
        "updated_at": str(step.updated_at) if step.updated_at else None,
    }


def serialize_campaign_recruiter(row: CampaignRecruiter) -> dict[str, Any]:
    recruiter = row.recruiter
    return {
        "campaign_recruiter_id": row.campaign_recruiter_id,
        "campaign_id": row.campaign_id,
        "recruiter_id": row.recruiter_id,
        "recruiter_name": recruiter.recruiter_name if recruiter else None,
        "recruiter_email": recruiter.email if recruiter else None,
        "company_id": recruiter.company_id if recruiter else None,
        "status": row.status,
        "current_step_id": row.current_step_id,
        "next_send_at": str(row.next_send_at) if row.next_send_at else None,
        "enrolled_at": str(row.enrolled_at) if row.enrolled_at else None,
        "sent_count": row.sent_count,
        "last_sent_at": str(row.last_sent_at) if row.last_sent_at else None,
        "opened_at": str(row.opened_at) if row.opened_at else None,
        "replied_at": str(row.replied_at) if row.replied_at else None,
        "bounced_at": str(row.bounced_at) if row.bounced_at else None,
        "completed_at": str(row.completed_at) if row.completed_at else None,
        "last_error": row.last_error,
        "variables": from_json_text(row.variables_json, {}),
        "metadata": from_json_text(row.metadata_json, {}),
    }

def serialize_campaign(c: Campaign):
    return {
        "campaign_id": c.campaign_id,
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "from_name": c.from_name,
        "from_email": c.from_email,
        "reply_to_email": c.reply_to_email,
        "start_at": c.start_at.isoformat() if c.start_at else None,
        "timezone": c.timezone,
        "is_active": c.is_active,
        "is_archived": c.is_archived,
        "rate_per_minute": c.rate_per_minute,
        "metadata": json.loads(c.metadata_json) if c.metadata_json else {},
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "template_count": getattr(c, "template_count", 0),
        "sequence_step_count": getattr(c, "sequence_step_count", 0),
        "recruiter_count": getattr(c, "recruiter_count", 0),
    }

def serialize_campaign_list(c: Campaign, stats: dict = None):
    stats = stats or {"total": 0, "sent": 0, "failed": 0, "progress_percent": 0}
    return {
        "campaign_id": c.campaign_id,
        "name": c.name,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "rate_per_minute": c.rate_per_minute,
        "stats": stats
    }


def get_campaign_or_404(db: Session, campaign_id: int, eager: bool = False) -> Campaign:
    query = db.query(Campaign)
    if eager:
        from sqlalchemy.orm import joinedload
        query = query.options(
            joinedload(Campaign.templates),
            joinedload(Campaign.sequence_steps),
            joinedload(Campaign.campaign_recruiters)
        )
    campaign = query.filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def get_template_or_404(db: Session, campaign_id: int, template_id: int) -> EmailTemplate:
    template = db.query(EmailTemplate).filter(
        EmailTemplate.campaign_id == campaign_id,
        EmailTemplate.template_id == template_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return template


def get_step_or_404(db: Session, campaign_id: int, step_id: int) -> SequenceStep:
    step = db.query(SequenceStep).filter(
        SequenceStep.campaign_id == campaign_id,
        SequenceStep.step_id == step_id,
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="Sequence step not found")
    return step


def get_first_active_step(campaign: Campaign) -> Optional[SequenceStep]:
    active_steps = [step for step in campaign.sequence_steps if step.is_active]
    if not active_steps:
        return None
    return sorted(active_steps, key=lambda item: item.step_order)[0]


class CampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = Field(default=CampaignStatus.draft.value)
    from_name: Optional[str] = Field(default=None, max_length=150)
    from_email: Optional[str] = Field(default=None, max_length=255)
    reply_to_email: Optional[str] = Field(default=None, max_length=255)
    start_at: Optional[datetime] = None
    timezone: Optional[str] = Field(default="UTC", max_length=100)
    is_active: bool = True
    metadata: Optional[dict[str, Any]] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    from_name: Optional[str] = Field(default=None, max_length=150)
    from_email: Optional[str] = Field(default=None, max_length=255)
    reply_to_email: Optional[str] = Field(default=None, max_length=255)
    start_at: Optional[datetime] = None
    timezone: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    variables: Optional[list[str]] = None
    is_active: bool = True


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=255)
    body: Optional[str] = Field(default=None, min_length=1)
    variables: Optional[list[str]] = None
    is_active: Optional[bool] = None


class SequenceStepCreate(BaseModel):
    template_id: int
    step_order: int = Field(ge=1)
    delay_days: int = Field(default=0, ge=0)
    delay_hours: int = Field(default=0, ge=0)
    is_active: bool = True


class SequenceStepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: Optional[int] = None
    step_order: Optional[int] = Field(default=None, ge=1)
    delay_days: Optional[int] = Field(default=None, ge=0)
    delay_hours: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class RecruiterEnrollmentItem(BaseModel):
    recruiter_id: int
    variables: Optional[dict[str, Any]] = None


class EnrollRecruitersRequest(BaseModel):
    recruiters: list[RecruiterEnrollmentItem]


class CampaignRecruiterStatusUpdate(BaseModel):
    status: str
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@router.get("/")
def list_campaigns(
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func, case
    
    query = db.query(
        Campaign,
        func.count(CampaignRecruiter.campaign_recruiter_id).label('total'),
        func.sum(case((CampaignRecruiter.status.in_(['Sent', 'Delivered', 'Opened', 'Replied', 'Bounced']), 1), else_=0)).label('sent'),
        func.sum(case((CampaignRecruiter.status == 'Failed', 1), else_=0)).label('failed')
    ).outerjoin(CampaignRecruiter, Campaign.campaign_id == CampaignRecruiter.campaign_id)
    
    if not include_archived:
        query = query.filter(Campaign.is_archived.is_(False))
        
    results = query.group_by(Campaign.campaign_id).order_by(Campaign.created_at.desc()).all()
    
    ret = []
    for c, total, sent, failed in results:
        t = total or 0
        s = sent or 0
        f = failed or 0
        p = round((s / t) * 100, 1) if t > 0 else 0
        stats = {"total": t, "sent": s, "failed": f, "progress_percent": p}
        ret.append(serialize_campaign_list(c, stats))
    return ret


@router.post("/")
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    from datetime import datetime
    now = datetime.utcnow()
    campaign = Campaign(
        name=payload.name.strip(),
        description=payload.description,
        status=payload.status,
        from_name=payload.from_name,
        from_email=payload.from_email,
        reply_to_email=payload.reply_to_email,
        start_at=payload.start_at,
        timezone=payload.timezone or "UTC",
        is_active=payload.is_active,
        metadata_json=to_json_text(payload.metadata),
        created_at=now,
        updated_at=now
    )
    db.add(campaign)
    db.commit()
    return serialize_campaign(campaign)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id, eager=True)
    payload = serialize_campaign(campaign)
    payload["templates"] = [serialize_template(item) for item in sorted(campaign.templates, key=lambda x: x.template_id)]
    payload["sequence_steps"] = [serialize_sequence_step(item) for item in sorted(campaign.sequence_steps, key=lambda x: x.step_order)]
    payload["campaign_recruiters"] = [serialize_campaign_recruiter(item) for item in campaign.campaign_recruiters]
    return payload


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    db.delete(campaign)
    db.commit()
    return {"status": "success", "message": "Campaign deleted"}


@router.post("/{campaign_id}/duplicate")
def duplicate_campaign(campaign_id: int, db: Session = Depends(get_db)):
    original = get_campaign_or_404(db, campaign_id)
    
    new_campaign = Campaign(
        name=f"{original.name} (Copy)",
        description=original.description,
        status=CampaignStatus.draft.value,
        from_name=original.from_name,
        from_email=original.from_email,
        reply_to_email=original.reply_to_email,
        timezone=original.timezone,
        is_active=True,
        metadata_json=original.metadata_json,
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    
    # Clone templates
    template_map = {}
    for t in original.templates:
        new_t = EmailTemplate(
            campaign_id=new_campaign.campaign_id,
            name=t.name,
            subject=t.subject,
            body=t.body,
            variables_json=t.variables_json,
            is_active=t.is_active
        )
        db.add(new_t)
        db.commit()
        db.refresh(new_t)
        template_map[t.template_id] = new_t.template_id
        
    # Clone sequence steps
    for s in original.sequence_steps:
        new_s = SequenceStep(
            campaign_id=new_campaign.campaign_id,
            template_id=template_map.get(s.template_id),
            step_order=s.step_order,
            delay_days=s.delay_days,
            delay_hours=s.delay_hours,
            is_active=s.is_active
        )
        db.add(new_s)
        
    db.commit()
    return {"status": "success", "campaign_id": new_campaign.campaign_id}


@router.put("/{campaign_id}")
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "metadata":
            campaign.metadata_json = to_json_text(value)
        else:
            setattr(campaign, field, value)
    db.commit()
    return serialize_campaign(campaign)


@router.delete("/{campaign_id}")
def archive_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    campaign.is_archived = True
    campaign.is_active = False
    campaign.status = CampaignStatus.archived.value
    db.commit()
    return {"message": "Campaign archived", "campaign": serialize_campaign(campaign)}


@router.get("/{campaign_id}/templates")
def list_templates(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    return [serialize_template(item) for item in sorted(campaign.templates, key=lambda x: x.template_id)]


@router.post("/{campaign_id}/templates")
def create_template(campaign_id: int, payload: TemplateCreate, request: Request, db: Session = Depends(get_db)):
    get_campaign_or_404(db, campaign_id)
    variables = payload.variables or extract_variables(payload.subject, payload.body)
    
    # Check if there is an existing step 1 template
    step = db.query(SequenceStep).filter(SequenceStep.campaign_id == campaign_id, SequenceStep.step_order == 1).first()
    
    if step and step.template_id:
        template = db.query(EmailTemplate).filter(EmailTemplate.template_id == step.template_id).first()
        if template:
            template.name = payload.name.strip()
            template.subject = payload.subject
            template.body = payload.body
            template.variables_json = to_json_text(variables)
            template.is_active = payload.is_active
            db.commit()
            db.refresh(template)
            return serialize_template(template)

    # Create new template if none exists
    template = EmailTemplate(
        campaign_id=campaign_id,
        name=payload.name.strip(),
        subject=payload.subject,
        body=payload.body,
        variables_json=to_json_text(variables),
        is_active=payload.is_active,
    )
    db.add(template)
    db.flush()
    
    if not step:
        step = SequenceStep(
            campaign_id=campaign_id,
            template_id=template.template_id,
            step_order=1,
            delay_days=0,
            delay_hours=0,
            is_active=True
        )
        db.add(step)
    else:
        step.template_id = template.template_id
        
    db.commit()
    db.refresh(template)
    return serialize_template(template)


@router.put("/{campaign_id}/templates/{template_id}")
def update_template(campaign_id: int, template_id: int, payload: TemplateUpdate, db: Session = Depends(get_db)):
    template = get_template_or_404(db, campaign_id, template_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "variables":
            template.variables_json = to_json_text(value)
        else:
            setattr(template, field, value)
    if template.variables_json is None:
        template.variables_json = to_json_text(extract_variables(template.subject, template.body))
    db.commit()
    db.refresh(template)
    return serialize_template(template)


@router.delete("/{campaign_id}/templates/{template_id}")
def deactivate_template(campaign_id: int, template_id: int, db: Session = Depends(get_db)):
    template = get_template_or_404(db, campaign_id, template_id)
    template.is_active = False
    db.commit()
    db.refresh(template)
    return {"message": "Template deactivated", "template": serialize_template(template)}


@router.get("/{campaign_id}/steps")
def list_sequence_steps(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    return [serialize_sequence_step(item) for item in sorted(campaign.sequence_steps, key=lambda x: x.step_order)]


@router.post("/{campaign_id}/steps")
def create_sequence_step(campaign_id: int, payload: SequenceStepCreate, db: Session = Depends(get_db)):
    get_campaign_or_404(db, campaign_id)
    template = get_template_or_404(db, campaign_id, payload.template_id)
    if not template.is_active:
        raise HTTPException(status_code=400, detail="Cannot attach an inactive template to a sequence step")
    step = SequenceStep(
        campaign_id=campaign_id,
        template_id=payload.template_id,
        step_order=payload.step_order,
        delay_days=payload.delay_days,
        delay_hours=payload.delay_hours,
        is_active=payload.is_active,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return serialize_sequence_step(step)


@router.put("/{campaign_id}/steps/{step_id}")
def update_sequence_step(campaign_id: int, step_id: int, payload: SequenceStepUpdate, db: Session = Depends(get_db)):
    step = get_step_or_404(db, campaign_id, step_id)
    updates = payload.model_dump(exclude_unset=True)
    if "template_id" in updates and updates["template_id"] is not None:
        get_template_or_404(db, campaign_id, updates["template_id"])
    for field, value in updates.items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return serialize_sequence_step(step)


@router.delete("/{campaign_id}/steps/{step_id}")
def deactivate_sequence_step(campaign_id: int, step_id: int, db: Session = Depends(get_db)):
    step = get_step_or_404(db, campaign_id, step_id)
    step.is_active = False
    db.commit()
    db.refresh(step)
    return {"message": "Sequence step deactivated", "step": serialize_sequence_step(step)}


@router.post("/{campaign_id}/enroll")
def enroll_recruiters(campaign_id: int, payload: EnrollRecruitersRequest, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    first_step = get_first_active_step(campaign)
    if not first_step:
        raise HTTPException(status_code=400, detail="Campaign must have at least one active sequence step to enroll recruiters")

    enrolled_count = 0
    for item in payload.recruiters:
        existing = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.recruiter_id == item.recruiter_id,
        ).first()
        if not existing:
            cr = CampaignRecruiter(
                campaign_id=campaign_id,
                recruiter_id=item.recruiter_id,
                current_step_id=first_step.step_id,
                status=CampaignRecruiterStatus.pending.value,
                enrolled_at=utcnow(),
                next_send_at=campaign.start_at or utcnow(),
                variables_json=to_json_text(item.variables),
            )
            db.add(cr)
            enrolled_count += 1

    db.commit()
    return {"message": f"Enrolled {enrolled_count} recruiters"}


@router.put("/{campaign_id}/recruiter/{recruiter_id}/status")
def update_recruiter_status(
    campaign_id: int,
    recruiter_id: int,
    payload: CampaignRecruiterStatusUpdate,
    db: Session = Depends(get_db),
):
    cr = db.query(CampaignRecruiter).filter(
        CampaignRecruiter.campaign_id == campaign_id,
        CampaignRecruiter.recruiter_id == recruiter_id,
    ).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    cr.status = payload.status
    if payload.opened_at:
        cr.opened_at = payload.opened_at
    if payload.replied_at:
        cr.replied_at = payload.replied_at
    if payload.bounced_at:
        cr.bounced_at = payload.bounced_at
    if payload.last_error:
        cr.last_error = payload.last_error
    if payload.metadata:
        current_meta = from_json_text(cr.metadata_json, {})
        current_meta.update(payload.metadata)
        cr.metadata_json = to_json_text(current_meta)

    db.commit()
    db.refresh(cr)
    return {"message": "Status updated", "enrollment": serialize_campaign_recruiter(cr)}
