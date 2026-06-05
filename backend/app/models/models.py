from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class PageVisit(Base):
    __tablename__ = "page_visits"
    id            = Column(Integer, primary_key=True, index=True)
    page          = Column(String(100), nullable=False)    # e.g. "Dashboard"
    path          = Column(String(100), nullable=False)    # e.g. "/"
    user_email    = Column(String(150), nullable=True)     # logged-in user email
    session_id    = Column(String(64),  nullable=True)     # browser session UUID
    time_on_page  = Column(Integer,     nullable=True)     # seconds spent on previous page
    user_agent    = Column(String(300), nullable=True)     # browser UA string
    ip_address    = Column(String(60),  nullable=True)     # client IP from request
    visited_at    = Column(TIMESTAMP, server_default=func.now(), index=True)

class ActionLog(Base):
    __tablename__ = "action_logs"
    id             = Column(Integer, primary_key=True, index=True)
    user_email     = Column(String(150), nullable=True)
    session_id     = Column(String(64), nullable=True, index=True)
    action_type    = Column(String(100), nullable=False)
    details        = Column(Text, nullable=True)
    status         = Column(String(50), default="success") # success, failed
    ip_address     = Column(String(60), nullable=True)
    created_at     = Column(TIMESTAMP, server_default=func.now(), index=True)


class Company(Base):
    __tablename__ = "companies"
    company_id   = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    normalized_company_name = Column(String(255), index=True, nullable=True)
    industry     = Column(String(100))
    location     = Column(String(150))
    state        = Column(String(2), index=True)
    website      = Column(String(255))
    email_pattern= Column(String(150))
    notes        = Column(Text)
    is_active    = Column(Boolean, default=True)
    data_source  = Column(String(100), default="manual")
    trust_score  = Column(Integer, default=100)
    source_job_id = Column(String(36), index=True, nullable=True)
    raw_data     = Column(Text, nullable=True)     # Original uploaded row (JSON string)
    metadata_json= Column(Text, nullable=True)     # Extra dynamic attributes (JSON string)
    tags         = Column(Text, nullable=True)     # Comma-separated tags or JSON list
    created_at   = Column(TIMESTAMP, server_default=func.now())
    updated_at   = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    recruiters   = relationship("Recruiter", back_populates="company")
    submissions  = relationship("Submission", back_populates="company")


class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id    = Column(Integer, primary_key=True, index=True)
    vendor_name  = Column(String(255), nullable=False)
    contact_name = Column(String(150))
    phone        = Column(String(30))
    location     = Column(String(150))
    created_at   = Column(TIMESTAMP, server_default=func.now())
    updated_at   = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    submissions  = relationship("Submission", back_populates="vendor")


class Recruiter(Base):
    __tablename__ = "recruiters"
    recruiter_id     = Column(Integer, primary_key=True, index=True)
    recruiter_name   = Column(String(150), nullable=False)
    normalized_recruiter_name = Column(String(150), index=True, nullable=True)
    email            = Column(String(150), unique=True, nullable=False)
    phone            = Column(String(30))
    email2           = Column(String(150))          # secondary / personal email
    phone2           = Column(String(30))           # secondary phone
    email3           = Column(String(150))
    phone3           = Column(String(30))
    email4           = Column(String(150))
    phone4           = Column(String(30))
    alternate_emails = Column(Text)                 # CSV of extra emails
    alternate_phones = Column(Text)                 # CSV of extra phones
    linkedin         = Column(String(255))
    specialization   = Column(String(150))
    title            = Column(String(150))
    notes            = Column(Text)                 # any extra info from messages etc.
    review_reason    = Column(Text)                 # Why it needs review
    company_id       = Column(Integer, ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True)
    location         = Column(String(255))
    state            = Column(String(2), index=True) # Normalized state
    normalized_city  = Column(String(150), index=True)
    location_confidence = Column(String(20), default="high") # high, low, manual_review
    completeness_score = Column(Integer, default=0, index=True)
    needs_review     = Column(Boolean, default=False, index=True)
    is_active        = Column(Boolean, default=True)
    data_source      = Column(String(100), default="manual")
    trust_score      = Column(Integer, default=100)
    source_job_id    = Column(String(36), index=True, nullable=True)
    raw_data         = Column(Text, nullable=True)     # Original uploaded row (JSON string)
    metadata_json    = Column(Text, nullable=True)     # Extra dynamic attributes (JSON string)
    tags             = Column(Text, nullable=True)     # Comma-separated tags or JSON list
    created_at       = Column(TIMESTAMP, server_default=func.now())
    updated_at       = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    company          = relationship("Company", back_populates="recruiters")
    candidates       = relationship("Candidate", back_populates="recruiter")
    submissions      = relationship("Submission", back_populates="recruiter")


class Candidate(Base):
    __tablename__ = "candidates"
    candidate_id     = Column(Integer, primary_key=True, index=True)
    candidate_name   = Column(String(150), nullable=False)
    email            = Column(String(150), unique=True, nullable=False)
    phone            = Column(String(30))
    linkedin         = Column(String(255))
    visa_status      = Column(String(50))
    skills           = Column(Text)
    experience_years = Column(Numeric(4, 1))
    location         = Column(String(150))
    rate_per_hour    = Column(Numeric(8, 2))
    availability     = Column(String(50))
    is_duplicate     = Column(Boolean, default=False)
    duplicate_of     = Column(Integer, ForeignKey("candidates.candidate_id", ondelete="SET NULL"), nullable=True)
    recruiter_id     = Column(Integer, ForeignKey("recruiters.recruiter_id", ondelete="SET NULL"), nullable=True)
    created_at       = Column(TIMESTAMP, server_default=func.now())
    updated_at       = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    recruiter        = relationship("Recruiter", back_populates="candidates")
    submissions      = relationship("Submission", back_populates="candidate")


class Submission(Base):
    __tablename__ = "submissions"
    submission_id   = Column(Integer, primary_key=True, index=True)
    candidate_id    = Column(Integer, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=False)
    recruiter_id    = Column(Integer, ForeignKey("recruiters.recruiter_id", ondelete="SET NULL"), nullable=True)
    company_id      = Column(Integer, ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True)
    vendor_id       = Column(Integer, ForeignKey("vendors.vendor_id", ondelete="SET NULL"), nullable=True)
    job_title       = Column(String(150))
    status          = Column(String(50), default="submitted")
    submission_date = Column(Date, server_default=func.current_date())
    interview_date  = Column(Date, nullable=True)
    notes           = Column(Text)
    created_at      = Column(TIMESTAMP, server_default=func.now())
    updated_at      = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    candidate       = relationship("Candidate", back_populates="submissions")
    recruiter       = relationship("Recruiter", back_populates="submissions")
    company         = relationship("Company", back_populates="submissions")
    vendor          = relationship("Vendor", back_populates="submissions")

class UploadJob(Base):
    __tablename__ = "upload_jobs"
    job_id          = Column(String(36), primary_key=True, index=True)
    filename        = Column(String(255), nullable=False)
    status          = Column(String(50), default="queued") # queued, processing, completed, failed
    current_step    = Column(String(100), nullable=True)
    progress_percent = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    total_rows      = Column(Integer, default=0)
    processed_rows  = Column(Integer, default=0)
    valid_rows      = Column(Integer, default=0)
    warning_rows    = Column(Integer, default=0)
    duplicate_rows  = Column(Integer, default=0)
    possible_duplicate_rows = Column(Integer, default=0)
    enriched_rows   = Column(Integer, default=0)
    failed_rows     = Column(Integer, default=0)
    inserted_rows   = Column(Integer, default=0)
    skipped_rows    = Column(Integer, default=0)
    error_count     = Column(Integer, default=0)
    error_message   = Column(Text, nullable=True)
    last_heartbeat_at = Column(TIMESTAMP, nullable=True)
    errors          = Column(Text, nullable=True) # JSON string of errors
    started_at      = Column(TIMESTAMP, server_default=func.now())
    completed_at    = Column(TIMESTAMP, nullable=True)
    updated_at      = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class RawUpload(Base):
    __tablename__ = "raw_uploads"
    id            = Column(Integer, primary_key=True, index=True)
    job_id        = Column(String(36), ForeignKey("upload_jobs.job_id", ondelete="CASCADE"), index=True)
    raw_data      = Column(Text) # JSON string of the exact raw row
    source_filename = Column(String(255))
    created_at    = Column(TIMESTAMP, server_default=func.now())

class StagingRecruiter(Base):
    __tablename__ = "staging_recruiters"
    id            = Column(Integer, primary_key=True, index=True)
    job_id        = Column(String(36), ForeignKey("upload_jobs.job_id", ondelete="CASCADE"), index=True)
    raw_upload_id = Column(Integer, ForeignKey("raw_uploads.id", ondelete="CASCADE"), nullable=True)
    recruiter_name= Column(String(255))
    email         = Column(String(255), index=True)
    phone         = Column(String(100))
    company_name  = Column(String(255))
    title         = Column(String(150))
    location      = Column(String(255))
    status        = Column(String(50), default="pending") # pending, processing, approved, rejected, duplicate, suspicious
    confidence_score = Column(Integer, default=0)
    errors        = Column(Text, nullable=True) # JSON list of validation errors
    created_at    = Column(TIMESTAMP, server_default=func.now())

class StagingCompany(Base):
    __tablename__ = "staging_companies"
    id            = Column(Integer, primary_key=True, index=True)
    job_id        = Column(String(36), ForeignKey("upload_jobs.job_id", ondelete="CASCADE"), index=True)
    company_name  = Column(String(255), index=True)
    location      = Column(String(255))
    industry      = Column(String(255))
    status        = Column(String(50), default="pending")
    confidence_score = Column(Integer, default=0)
    created_at    = Column(TIMESTAMP, server_default=func.now())




class PlatformUpdate(Base):
    __tablename__ = "platform_updates"
    
    update_id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    developer = Column(String(100), default="System")
    
    features = relationship("FeatureVerification", back_populates="update")

class FeatureVerification(Base):
    __tablename__ = "feature_verifications"
    
    feature_id = Column(Integer, primary_key=True, index=True)
    update_id = Column(Integer, ForeignKey("platform_updates.update_id"))
    feature_name = Column(String(255), nullable=False)
    status = Column(String(50), default="Pending Verification") # Pending Verification, Verified, Failed Verification
    last_tested = Column(TIMESTAMP, nullable=True)
    tester = Column(String(100), nullable=True)
    result = Column(Text, nullable=True)
    
    update = relationship("PlatformUpdate", back_populates="features")



class SmartImportJob(Base):
    __tablename__ = "smart_import_jobs"
    job_id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="mapping") # mapping, validating, reviewing, importing, completed, failed
    current_step = Column(String(100), nullable=True)
    progress_percent = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    warning_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    possible_duplicate_rows = Column(Integer, default=0)
    enriched_rows = Column(Integer, default=0)
    inserted_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    started_at = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    last_heartbeat_at = Column(TIMESTAMP, nullable=True)
    error_message = Column(Text, nullable=True)
    user_email = Column(String(150), nullable=True)
    column_mapping = Column(Text, nullable=True) # JSON string of confirmed mapping
    detected_format = Column(String(100), default="standard_row")
    format_confidence = Column(Integer, default=100)
    
    rows = relationship("SmartImportRow", back_populates="job", cascade="all, delete-orphan")


class SmartImportRow(Base):
    __tablename__ = "smart_import_rows"
    row_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("smart_import_jobs.job_id", ondelete="CASCADE"), index=True)
    original_row_index = Column(Integer)
    
    # Normalized Fields
    recruiter_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company_name = Column(String(255), nullable=True)
    state = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    specialization = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Raw Data for fallback/reference
    raw_json = Column(Text)
    
    # Validation Data
    status = Column(String(50), default="Ready") # Ready, Warning, Error, Duplicate, Needs Review
    validation_issues = Column(Text) # JSON list of strings
    
    job = relationship("SmartImportJob", back_populates="rows")
