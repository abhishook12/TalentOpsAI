"""
email_intel.py — REST API endpoints for Corporate Email Guesser & MX Verifier Engine.
Provides interactive resolution, MX verification, pattern learning, and pattern directory.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from ..models.models import CompanyEmailPattern, Company, Recruiter
from ..models.auth_models import User
from ..routes.auth import get_current_user_from_request
from ..services.email_intelligence_service import email_intelligence

router = APIRouter(prefix="/api/email-intel", tags=["Email Intelligence"])


# ── Pydantic Request & Response Schemas ───────────────────────────────────────

class EmailResolveRequest(BaseModel):
    full_name: str = Field(..., description="Full name of candidate (e.g., 'Satya Nadella')")
    company_name: str = Field(..., description="Target company name (e.g., 'Microsoft')")
    existing_email: Optional[str] = Field(None, description="Known candidate email if available")


class MxVerifyRequest(BaseModel):
    domain: str = Field(..., description="Domain name to verify MX records for (e.g., 'stripe.com')")


class LearnPatternRequest(BaseModel):
    email: str = Field(..., description="Observed corporate email (e.g., 'alex.russell@stripe.com')")
    full_name: str = Field(..., description="Candidate full name (e.g., 'Alex Russell')")
    company_name: Optional[str] = Field(None, description="Company name")


class PatternResponse(BaseModel):
    id: int
    company_id: int
    domain: str
    pattern: str
    confidence_score: int
    verified_example_count: int
    active: bool
    last_verified_at: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/resolve")
def resolve_candidate_email(
    req: EmailResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Synthesize and verify the corporate email for a candidate using domain heuristics,
    learned company patterns, and DNS MX exchanger checks.
    """
    if not req.full_name or not req.company_name:
        raise HTTPException(status_code=400, detail="full_name and company_name are required.")

    result = email_intelligence.resolve_and_enrich_candidate(
        full_name=req.full_name,
        company_name=req.company_name,
        existing_email=req.existing_email,
        db=db,
    )

    return {
        "success": True,
        "input": {
            "full_name": req.full_name,
            "company_name": req.company_name,
            "existing_email": req.existing_email,
        },
        "resolution": result,
    }


@router.post("/verify-mx")
def verify_domain_mx(
    req: MxVerifyRequest,
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Performs live DNS MX verification on a domain and returns provider fingerprint.
    """
    if not req.domain:
        raise HTTPException(status_code=400, detail="domain is required.")

    clean_dom = req.domain.lower().replace("www.", "").strip()
    mx_data = email_intelligence.verify_mx(clean_dom)

    return {
        "domain": clean_dom,
        "is_valid": mx_data["is_valid"],
        "has_mx": mx_data["has_mx"],
        "provider": mx_data["provider"],
        "mx_records": mx_data["mx_records"],
        "cached": mx_data.get("cached", False),
    }


@router.post("/learn")
def learn_company_pattern(
    req: LearnPatternRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Reverse-engineers and saves a company's email formula from an observed email address.
    """
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Valid email is required.")
    if not req.full_name:
        raise HTTPException(status_code=400, detail="full_name is required.")

    pattern = email_intelligence.learn_pattern_from_email(
        email=req.email,
        full_name=req.full_name,
        company_name=req.company_name,
        db=db,
    )

    if not pattern:
        return {
            "success": False,
            "message": "Could not deduce pattern (may be a personal email domain or non-standard local part).",
            "email": req.email,
        }

    domain = req.email.split("@")[1].lower().strip()
    return {
        "success": True,
        "email": req.email,
        "domain": domain,
        "deduced_pattern": pattern,
    }


@router.get("/patterns")
def list_email_patterns(
    search: Optional[str] = Query(None, description="Search domain or pattern"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Lists known and self-learned company email patterns.
    """
    query = db.query(CompanyEmailPattern).filter(CompanyEmailPattern.active == True)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            (CompanyEmailPattern.domain.ilike(s)) |
            (CompanyEmailPattern.pattern.ilike(s))
        )

    patterns = query.order_by(
        CompanyEmailPattern.verified_example_count.desc(),
        CompanyEmailPattern.confidence_score.desc()
    ).limit(limit).all()

    return {
        "count": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "company_id": p.company_id,
                "domain": p.domain,
                "pattern": p.pattern,
                "confidence_score": p.confidence_score,
                "verified_example_count": p.verified_example_count,
                "active": p.active,
                "last_verified_at": p.last_verified_at.isoformat() if p.last_verified_at else None,
            }
            for p in patterns
        ]
    }


@router.get("/stats")
def get_email_intel_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Overview statistics of company pattern coverage and candidate synthesis.
    """
    total_patterns = db.query(func.count(CompanyEmailPattern.id)).scalar() or 0
    total_domains_covered = db.query(func.count(func.distinct(CompanyEmailPattern.domain))).scalar() or 0
    high_confidence_patterns = db.query(func.count(CompanyEmailPattern.id)).filter(
        CompanyEmailPattern.confidence_score >= 80
    ).scalar() or 0

    synthesized_candidates = db.query(func.count(Recruiter.recruiter_id)).filter(
        Recruiter.email_generated == True
    ).scalar() or 0

    pattern_verified_candidates = db.query(func.count(Recruiter.recruiter_id)).filter(
        Recruiter.email_status == "PATTERN_VERIFIED"
    ).scalar() or 0

    return {
        "total_patterns_learned": total_patterns,
        "total_domains_covered": total_domains_covered,
        "high_confidence_patterns": high_confidence_patterns,
        "candidates_synthesized": synthesized_candidates,
        "pattern_verified_candidates": pattern_verified_candidates,
        "in_memory_cached_mx_domains": len(email_intelligence._MX_CACHE) if hasattr(email_intelligence, "_MX_CACHE") else 0,
    }
