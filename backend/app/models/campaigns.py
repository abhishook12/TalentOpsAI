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
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base, engine


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class CampaignRecruiterStatus(str, Enum):
    pending = "Pending"
    sent = "Sent"
    opened = "Opened"
    replied = "Replied"
    bounced = "Bounced"
    failed = "Failed"


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

    campaign = relationship("Campaign", back_populates="campaign_recruiters")
    current_step = relationship("SequenceStep", back_populates="campaign_recruiters")
    recruiter = relationship("Recruiter")

    def variables_dict(self):
        if not self.variables_json:
            return {}
        try:
            return json.loads(self.variables_json)
        except json.JSONDecodeError:
            return {}


def ensure_campaign_tables():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Campaign.__table__,
            EmailTemplate.__table__,
            SequenceStep.__table__,
            CampaignRecruiter.__table__,
        ],
    )

