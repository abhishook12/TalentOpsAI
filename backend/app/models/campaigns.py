import json
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql import func, select

from ..database import Base, engine


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"
    archived = "archived"
    failed = "failed"


class CampaignRecruiterStatus(str, Enum):
    pending = "Pending"
    queued = "Queued"
    sending = "Sending"
    sent = "Sent"
    delivered = "Delivered"
    opened = "Opened"
    replied = "Replied"
    bounced = "Bounced"
    failed = "Failed"
    retrying = "Retrying"
    cancelled = "Cancelled"


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default=CampaignStatus.draft.value, index=True)
    from_name = Column(String(150), nullable=True)
    from_email = Column(String(255), nullable=True)
    reply_to_email = Column(String(255), nullable=True)
    start_at = Column(TIMESTAMP, nullable=True)
    timezone = Column(String(100), nullable=True, default="UTC")
    is_active = Column(Boolean, default=True, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    rate_per_minute = Column(Integer, default=4, nullable=False)  # Configurable send speed
    signature_id = Column(Integer, ForeignKey("email_signatures.signature_id", ondelete="SET NULL"), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    templates = relationship("EmailTemplate", back_populates="campaign", cascade="all, delete-orphan")
    sequence_steps = relationship("SequenceStep", back_populates="campaign", cascade="all, delete-orphan")
    campaign_recruiters = relationship("CampaignRecruiter", back_populates="campaign", cascade="all, delete-orphan")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    template_id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    variables_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    campaign = relationship("Campaign", back_populates="templates")
    sequence_steps = relationship("SequenceStep", back_populates="template")


class SequenceStep(Base):
    __tablename__ = "sequence_steps"
    __table_args__ = (
        UniqueConstraint("campaign_id", "step_order", name="uq_sequence_steps_campaign_order"),
    )

    step_id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("email_templates.template_id", ondelete="RESTRICT"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    delay_days = Column(Integer, default=0, nullable=False)
    delay_hours = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    campaign = relationship("Campaign", back_populates="sequence_steps")
    template = relationship("EmailTemplate", back_populates="sequence_steps")
    campaign_recruiters = relationship("CampaignRecruiter", back_populates="current_step")


class CampaignRecruiter(Base):
    __tablename__ = "campaign_recruiters"
    __table_args__ = (
        UniqueConstraint("campaign_id", "recruiter_id", name="uq_campaign_recruiter_campaign_id_recruiter_id"),
    )

    campaign_recruiter_id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"), nullable=False, index=True)
    current_step_id = Column(Integer, ForeignKey("sequence_steps.step_id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default=CampaignRecruiterStatus.pending.value, index=True)
    next_send_at = Column(TIMESTAMP, nullable=True, index=True)
    enrolled_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    last_sent_at = Column(TIMESTAMP, nullable=True)
    opened_at = Column(TIMESTAMP, nullable=True)
    replied_at = Column(TIMESTAMP, nullable=True)
    bounced_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    last_error = Column(Text, nullable=True)
    variables_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # New columns for campaign engine
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    sent_via = Column(String(50), nullable=True)  # 'outlook_bridge' or 'smtp'
    queue_position = Column(Integer, nullable=True, index=True)

    campaign = relationship("Campaign", back_populates="campaign_recruiters")
    current_step = relationship("SequenceStep", back_populates="campaign_recruiters")
    recruiter = relationship("Recruiter")
    email_logs = relationship("EmailLog", back_populates="campaign_recruiter", cascade="all, delete-orphan")

    def variables_dict(self):
        if not self.variables_json:
            return {}
        try:
            return json.loads(self.variables_json)
        except json.JSONDecodeError:
            return {}


class EmailLogStatus(str, Enum):
    queued = "queued"
    sending = "sending"
    delivered = "delivered"
    failed = "failed"
    retrying = "retrying"
    rejected = "rejected"
    cancelled = "cancelled"
    bounced = "bounced"


class EmailLog(Base):
    """Per-email delivery log with full lifecycle tracking."""
    __tablename__ = "email_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_recruiter_id = Column(Integer, ForeignKey("campaign_recruiters.campaign_recruiter_id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=True)

    # Delivery lifecycle
    status = Column(String(50), default=EmailLogStatus.queued.value, nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)

    # What was sent
    subject = Column(String(500), nullable=True)
    body_preview = Column(Text, nullable=True)  # First 200 chars of body for logging
    body_html = Column(Text, nullable=True)  # Full HTML handed to the bridge; cleared once send is terminal to keep DB small (Supabase free tier)
    sent_via = Column(String(50), nullable=True)  # 'outlook_bridge' or 'smtp'

    # Verification
    outlook_accepted = Column(Boolean, nullable=True)
    sent_folder_updated = Column(Boolean, nullable=True)
    smtp_response = Column(Text, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_category = Column(String(100), nullable=True)  # 'mailbox_full', 'dns_failure', 'smtp_timeout', 'auth_error', 'network_lost'

    # Timing
    queued_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    sending_at = Column(TIMESTAMP, nullable=True)
    delivered_at = Column(TIMESTAMP, nullable=True)
    failed_at = Column(TIMESTAMP, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # How long the send took

    # Relationships
    campaign_recruiter = relationship("CampaignRecruiter", back_populates="email_logs")


class CampaignDraft(Base):
    """Auto-saved draft state for crash recovery."""
    __tablename__ = "campaign_drafts"

    draft_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)

    # Campaign reference (null if not yet created as a campaign)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id", ondelete="SET NULL"), nullable=True, index=True)

    # Draft content
    campaign_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    cc = Column(String(500), nullable=True)
    bcc = Column(String(500), nullable=True)
    recipients_json = Column(Text, nullable=True)  # JSON array of email addresses

    # Queue state (for pause/resume recovery)
    queue_position = Column(Integer, nullable=True)
    total_recipients = Column(Integer, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailSignature(Base):
    """User-managed email signatures."""
    __tablename__ = "email_signatures"

    signature_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Work Signature", "Formal"
    html_content = Column(Text, nullable=False)  # Rich HTML signature content
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)


# N+1 Query Optimization: Compute counts dynamically in the main query rather than via relationships
Campaign.template_count = column_property(
    select(func.count(EmailTemplate.template_id))
    .where(EmailTemplate.campaign_id == Campaign.campaign_id)
    .correlate_except(EmailTemplate)
    .scalar_subquery()
)

Campaign.sequence_step_count = column_property(
    select(func.count(SequenceStep.step_id))
    .where(SequenceStep.campaign_id == Campaign.campaign_id)
    .correlate_except(SequenceStep)
    .scalar_subquery()
)

Campaign.recruiter_count = column_property(
    select(func.count(CampaignRecruiter.campaign_recruiter_id))
    .where(CampaignRecruiter.campaign_id == Campaign.campaign_id)
    .correlate_except(CampaignRecruiter)
    .scalar_subquery()
)


def ensure_campaign_tables():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            EmailSignature.__table__,
            Campaign.__table__,
            EmailTemplate.__table__,
            SequenceStep.__table__,
            CampaignRecruiter.__table__,
            EmailLog.__table__,
            CampaignDraft.__table__,
        ],
    )
