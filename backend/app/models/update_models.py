"""
update_models.py — SQLAlchemy Models for Scout Release Distribution & Fleet Telemetry.

Tables:
- scout_releases: Published software versions, channels, SHA-256 hashes, minimum versions, and remote feature flags.
- scout_installations: Real-time telemetry tracking desktop installations across the fleet.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    TIMESTAMP,
    ForeignKey,
)
from sqlalchemy.sql import func
from ..database import Base


class ScoutRelease(Base):
    """Catalog of official releases across deployment channels (stable, beta, internal)."""
    __tablename__ = "scout_releases"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(32), unique=True, index=True, nullable=False)        # e.g. "2.4.0"
    channel = Column(String(32), default="stable", index=True, nullable=False)   # stable, beta, internal
    minimum_version = Column(String(32), default="1.0.0", nullable=False)        # Deprecation floor
    mandatory = Column(Boolean, default=False)
    download_url = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=True)                                   # Cryptographic hash
    size_bytes = Column(Integer, nullable=True)
    release_notes = Column(Text, nullable=True)
    features_json = Column(Text, default="{}")                                   # Remote feature flags
    config_json = Column(Text, default="{}")                                     # Runtime config overrides
    status = Column(String(32), default="ACTIVE", index=True)                    # ACTIVE, DEPRECATED
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)


class ScoutInstallation(Base):
    """Fleet telemetry tracking version adoption and update health across devices."""
    __tablename__ = "scout_installations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    scout_version = Column(String(32), index=True, nullable=False)
    channel = Column(String(32), default="stable")
    os_info = Column(String(100), nullable=True)
    update_status = Column(String(32), default="UP_TO_DATE", index=True)         # UP_TO_DATE, DOWNLOADING, STAGED, FAILED, ROLLED_BACK
    error_message = Column(Text, nullable=True)
    queue_size = Column(Integer, default=0)
    last_check_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_update_at = Column(TIMESTAMP, nullable=True)
