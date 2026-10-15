from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from ..database import Base

class OutlookFeedbackLog(Base):
    __tablename__ = "outlook_feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String(255), unique=True, index=True, nullable=False)
    folder_name = Column(String(100), index=True, nullable=False)
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=True)
    recipient_email = Column(String(255), index=True, nullable=False)
    event_type = Column(String(50), index=True, default="hard_bounce") # hard_bounce, soft_bounce, delivered
    smtp_code = Column(String(50), nullable=True)
    diagnostic_reason = Column(Text, nullable=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.campaign_id', ondelete='SET NULL'), nullable=True, index=True)
    recruiter_id = Column(Integer, ForeignKey('recruiters.recruiter_id', ondelete='SET NULL'), nullable=True, index=True)
    received_at = Column(TIMESTAMP, nullable=True, index=True)
    processed_at = Column(TIMESTAMP, server_default=func.now(), index=True)
