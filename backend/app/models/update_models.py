"""
update_models.py — SQLAlchemy Models for Scout Release Distribution & Fleet Telemetry.

Tables:
- scout_releases: Published software versions, channels, SHA-256 hashes, digital signatures,
  staged rollout controls, circuit breaker thresholds, and remote feature flags.
- scout_installations: Real-time telemetry tracking desktop installations across the fleet,
  including node health classification (HEALTHY, STALE, UPDATE_FAILED, OFFLINE).
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    Float,
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
    status = Column(String(32), default="ACTIVE", index=True)                    # ACTIVE, DEPRECATED, CIRCUIT_TRIPPED

    # Cryptographic Trust Chain
    signature = Column(Text, nullable=True)                                      # Ed25519 manifest digital signature
    package_signature = Column(Text, nullable=True)                              # Ed25519 package digital signature

    # Staged Rollout & Circuit Breaker Controls
    rollout_percentage = Column(Integer, default=100)                           # 0 - 100% rollout gating
    is_paused = Column(Boolean, default=False)                                   # Manual or automatic rollout pause
    failure_threshold_pct = Column(Float, default=3.0)                           # Circuit breaker trips when failure rate > 3%
    failure_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    @property
    def failure_rate(self) -> float:
        total = self.failure_count + self.success_count
        if total == 0:
            return 0.0
        return round((self.failure_count / total) * 100.0, 2)


class ScoutInstallation(Base):
    """Fleet telemetry tracking version adoption, health classification, and update lifecycle."""
    __tablename__ = "scout_installations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    installation_id = Column(String(64), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    scout_version = Column(String(32), index=True, nullable=False)
    channel = Column(String(32), default="stable", index=True)
    os_info = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    
    # State Machine & Lifecycle Status
    update_status = Column(String(32), default="UP_TO_DATE", index=True)         # UP_TO_DATE, DOWNLOADING, STAGED, FAILED, ROLLBACK, etc.
    update_attempts = Column(Integer, default=0)
    current_release = Column(String(32), nullable=True)
    last_error = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    queue_size = Column(Integer, default=0)

    # Health status classification: HEALTHY, STALE, UPDATE_FAILED, OFFLINE
    health_status = Column(String(32), default="HEALTHY", index=True)

    # Timestamps
    last_seen = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_check_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_update_check = Column(TIMESTAMP, nullable=True)
    last_update_at = Column(TIMESTAMP, nullable=True)
    last_successful_update = Column(TIMESTAMP, nullable=True)
