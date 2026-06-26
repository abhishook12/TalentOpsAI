import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    ensure_campaign_tables,
)
from ..models.models import Recruiter

router = APIRouter()
ensure_campaign_tables()


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


def serialize_campaign(campaign: Campaign) -> dict[str, Any]:
    return {
        "campaign_id": campaign.campaign_id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "from_name": campaign.from_name,
        "from_email": campaign.from_email,
        "reply_to_email": campaign.reply_to_email,
        "start_at": str(campaign.start_at) if campaign.start_at else None,
        "timezone": campaign.timezone,
        "is_active": campaign.is_active,
        "is_archived": campaign.is_archived,
        "metadata": from_json_text(campaign.metadata_json, {}),
        "created_at": str(campaign.created_at) if campaign.created_at else None,
        "updated_at": str(campaign.updated_at) if campaign.updated_at else None,
        "template_count": len(campaign.templates or []),
        "sequence_step_count": len(campaign.sequence_steps or []),
        "recruiter_count": len(campaign.campaign_recruiters or []),
    }


def get_campaign_or_404(db: Session, campaign_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
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
    query = db.query(Campaign)
    if not include_archived:
        query = query.filter(Campaign.is_archived.is_(False))
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return [serialize_campaign(campaign) for campaign in campaigns]


@router.post("/")
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
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
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return serialize_campaign(campaign)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    payload = serialize_campaign(campaign)
    payload["templates"] = [serialize_template(item) for item in sorted(campaign.templates, key=lambda x: x.template_id)]
    payload["sequence_steps"] = [serialize_sequence_step(item) for item in sorted(campaign.sequence_steps, key=lambda x: x.step_order)]
    payload["campaign_recruiters"] = [serialize_campaign_recruiter(item) for item in campaign.campaign_recruiters]
    return payload


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
    db.refresh(campaign)
    return serialize_campaign(campaign)


@router.delete("/{campaign_id}")
def archive_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    campaign.is_archived = True
    campaign.is_active = False
    campaign.status = CampaignStatus.archived.value
    db.commit()
    db.refresh(campaign)
    return {"message": "Campaign archived", "campaign": serialize_campaign(campaign)}


@router.get("/{campaign_id}/templates")
def list_templates(campaign_id: int, db: Session = Depends(get_db)):
    campaign = get_campaign_or_404(db, campaign_id)
    return [serialize_template(item) for item in sorted(campaign.templates, key=lambda x: x.template_id)]


@router.post("/{campaign_id}/templates")
def create_template(campaign_id: int, payload: TemplateCreate, db: Session = Depends(get_db)):
    get_campaign_or_404(db, campaign_id)
    variables = payload.variables or extract_variables(payload.subject, payload.body)
    template = EmailTemplate(
        campaign_id=campaign_id,
        name=payload.name.strip(),
        subject=payload.subject,
        body=payload.body,
        variables_json=to_json_text(variables),
        is_active=payload.is_active,
    )
    db.add(template)
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
        raise HTTPException(status_code=400, detail="Campaign must have at least one active sequence step before enrollment")

    recruiter_ids = [item.recruiter_id for item in payload.recruiters]
    recruiters = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(recruiter_ids)).all()
    recruiter_map = {recruiter.recruiter_id: recruiter for recruiter in recruiters}
    missing = sorted(set(recruiter_ids) - set(recruiter_map))
    if missing:
        raise HTTPException(status_code=404, detail=f"Recruiters not found: {missing}")

    enrolled = []
    skipped = []
    for item in payload.recruiters:
        existing = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.recruiter_id == item.recruiter_id,
        ).first()
        if existing:
            skipped.append(item.recruiter_id)
            continue

        next_send_at = campaign.start_at or utcnow()
        row = CampaignRecruiter(
            campaign_id=campaign_id,
            recruiter_id=item.recruiter_id,
            current_step_id=first_step.step_id,
            status=CampaignRecruiterStatus.pending.value,
            next_send_at=next_send_at,
            variables_json=to_json_text(item.variables or {}),
        )
        db.add(row)
        enrolled.append(item.recruiter_id)

    db.commit()
    return {"campaign_id": campaign_id, "enrolled_recruiter_ids": enrolled, "skipped_existing_recruiter_ids": skipped}


@router.get("/{campaign_id}/recruiters")
def list_campaign_recruiters(
    campaign_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    get_campaign_or_404(db, campaign_id)
    query = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == campaign_id)
    if status:
        query = query.filter(CampaignRecruiter.status == status)
    rows = query.order_by(CampaignRecruiter.created_at.desc()).all()
    return [serialize_campaign_recruiter(row) for row in rows]


@router.patch("/{campaign_id}/recruiters/{campaign_recruiter_id}/status")
def update_campaign_recruiter_status(
    campaign_id: int,
    campaign_recruiter_id: int,
    payload: CampaignRecruiterStatusUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(CampaignRecruiter).filter(
        CampaignRecruiter.campaign_id == campaign_id,
        CampaignRecruiter.campaign_recruiter_id == campaign_recruiter_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign recruiter row not found")

    row.status = payload.status
    if payload.opened_at is not None:
        row.opened_at = payload.opened_at
    if payload.replied_at is not None:
        row.replied_at = payload.replied_at
    if payload.bounced_at is not None:
        row.bounced_at = payload.bounced_at
    if payload.last_error is not None:
        row.last_error = payload.last_error
    if payload.metadata is not None:
        row.metadata_json = to_json_text(payload.metadata)
    if payload.status in {CampaignRecruiterStatus.replied.value, CampaignRecruiterStatus.bounced.value}:
        row.completed_at = row.completed_at or utcnow()
    db.commit()
    db.refresh(row)
    return serialize_campaign_recruiter(row)


@router.get("/{campaign_id}/analytics")
def get_campaign_analytics(campaign_id: int, db: Session = Depends(get_db)):
    get_campaign_or_404(db, campaign_id)
    rows = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == campaign_id).all()

    total = len(rows)
    sent = sum(1 for row in rows if row.status in {
        CampaignRecruiterStatus.sent.value,
        CampaignRecruiterStatus.opened.value,
        CampaignRecruiterStatus.replied.value,
        CampaignRecruiterStatus.bounced.value,
    })
    opened = sum(1 for row in rows if row.status in {
        CampaignRecruiterStatus.opened.value,
        CampaignRecruiterStatus.replied.value,
    })
    replied = sum(1 for row in rows if row.status == CampaignRecruiterStatus.replied.value)
    bounced = sum(1 for row in rows if row.status == CampaignRecruiterStatus.bounced.value)
    pending = sum(1 for row in rows if row.status == CampaignRecruiterStatus.pending.value)
    failed = sum(1 for row in rows if row.status == CampaignRecruiterStatus.failed.value)

    return {
        "campaign_id": campaign_id,
        "total_enrolled": total,
        "pending": pending,
        "sent": sent,
        "opened": opened,
        "replied": replied,
        "bounced": bounced,
        "failed": failed,
        "open_rate_percent": round((opened / sent) * 100, 2) if sent else 0.0,
        "reply_rate_percent": round((replied / sent) * 100, 2) if sent else 0.0,
        "bounce_rate_percent": round((bounced / sent) * 100, 2) if sent else 0.0,
        "step_count": db.query(func.count(SequenceStep.step_id)).filter(SequenceStep.campaign_id == campaign_id, SequenceStep.is_active.is_(True)).scalar() or 0,
        "template_count": db.query(func.count(EmailTemplate.template_id)).filter(EmailTemplate.campaign_id == campaign_id, EmailTemplate.is_active.is_(True)).scalar() or 0,
    }

