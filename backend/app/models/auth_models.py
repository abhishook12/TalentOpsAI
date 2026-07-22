from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

class RolePermission(Base):
    __tablename__ = 'role_permissions'
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)

class UserPermission(Base):
    __tablename__ = 'user_permissions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)

class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(String(50), nullable=True)
    max_seats = Column(Integer, nullable=True)
    features = Column(Text, nullable=True)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    start_date = Column(DateTime, server_default=func.now())
    renewal_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    status = Column(String(50), default='active')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True) # Changed for OAuth
    auth_provider = Column(String(50), default='local')
    provider_id = Column(String(255), nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(String(50), default='Pending Verification')
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)
    org_id = Column(Integer, ForeignKey('organizations.id'), nullable=True)
    
    # Expanded Profile & Identity
    job_title = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    work_email = Column(String(150), nullable=True)
    alt_email = Column(String(150), nullable=True)
    timezone = Column(String(100), nullable=True, default="UTC")
    address = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    resume_url = Column(String(500), nullable=True)
    
    # Global Preferences
    default_sender_id = Column(Integer, nullable=True) # Will map to UserOutlookAccount
    default_reply_to = Column(String(150), nullable=True)
    signature_html = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    role = relationship("Role")

class TrustedDevice(Base):
    __tablename__ = 'trusted_devices'
    id = Column(Integer, primary_key=True, index=True)
    device_id_hash = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    browser = Column(String(255), nullable=True)
    os = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    device_type = Column(String(100), nullable=True)
    browser_version = Column(String(100), nullable=True)
    timezone = Column(String(100), nullable=True)
    language = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    ip_address = Column(String(60), nullable=True)
    login_attempts = Column(Integer, default=1)
    risk_level = Column(String(50), default='low') # low, medium, high
    first_seen = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
    status = Column(String(50), default='Pending') # Pending, Trusted, Revoked, Disabled, Blocked
    approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", foreign_keys=[user_id])

class Session(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    trusted_device_id = Column(Integer, ForeignKey('trusted_devices.id', ondelete='CASCADE'), nullable=True)
    device = Column(String(255), nullable=True)
    browser = Column(String(255), nullable=True)
    ip_address = Column(String(60), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class LoginHistory(Base):
    __tablename__ = 'login_history'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    email = Column(String(150), nullable=True)
    status = Column(String(50), nullable=False) # success, failed
    reason = Column(String(255), nullable=True)
    ip_address = Column(String(60), nullable=True)
    browser = Column(String(255), nullable=True)
    os = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(255), nullable=False)
    target_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    target_device_id = Column(Integer, ForeignKey('trusted_devices.id', ondelete='SET NULL'), nullable=True)
    reason = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    ip_address = Column(String(60), nullable=True)
    device = Column(String(255), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)

class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

class APIKey(Base):
    __tablename__ = 'api_keys'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

class UserOutlookAccount(Base):
    __tablename__ = 'user_outlook_accounts'
    account_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    email_address = Column(String(255), nullable=False)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    status = Column(String(50), default="disconnected") # connected, disconnected, expired
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
class UserBridgeStatus(Base):
    __tablename__ = 'user_bridge_status'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    status = Column(String(50), default="offline") # online, offline, error
    last_heartbeat = Column(DateTime, nullable=True)
    uptime_seconds = Column(Integer, default=0)
    last_successful_email_at = Column(DateTime, nullable=True)
    consecutive_errors = Column(Integer, default=0)
    version = Column(String(50), nullable=True)
    diagnostics_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    preferences = Column(Text, nullable=True) # JSON stored as string for cross-db compat, or JSON type
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
