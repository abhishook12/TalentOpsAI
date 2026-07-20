import datetime
from sqlalchemy import Column, String, DateTime
from app.database import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
