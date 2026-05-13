from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, Text, ARRAY, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Company(Base):
    __tablename__ = "companies"
    company_id   = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    industry     = Column(String(100))
    location     = Column(String(150))
    website      = Column(String(255))
    created_at   = Column(TIMESTAMP, server_default=func.now())
    updated_at   = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    recruiters   = relationship("Recruiter", back_populates="company")
    submissions  = relationship("Submission", back_populates="company")


class Vendor(Base):
    __tablename__ = "vendors"
    vendor_id    = Column(Integer, primary_key=True, index=True)
    vendor_name  = Column(String(255), nullable=False)
    contact_name = Column(String(150))
    email        = Column(String(150), unique=True)
    phone        = Column(String(30))
    location     = Column(String(150))
    created_at   = Column(TIMESTAMP, server_default=func.now())
    updated_at   = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    submissions  = relationship("Submission", back_populates="vendor")


class Recruiter(Base):
    __tablename__ = "recruiters"
    recruiter_id     = Column(Integer, primary_key=True, index=True)
    recruiter_name   = Column(String(150), nullable=False)
    email            = Column(String(150), unique=True, nullable=False)
    phone            = Column(String(30))
    linkedin         = Column(String(255))
    specialization   = Column(String(150))
    company_id       = Column(Integer, ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True)
    is_active        = Column(Boolean, default=True)
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
    skills           = Column(ARRAY(Text))
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
