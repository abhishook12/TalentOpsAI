"""
Domain Health & Deliverability Inspector Routes
Provides DNS/SPF/DKIM/DMARC analysis for email deliverability assurance.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.auth_service import get_current_user_from_request
from ..services.domain_health import check_domain_health, get_warmup_schedule
from ..models.auth_models import User

router = APIRouter(prefix="/domain-health", tags=["Domain Health"])

@router.get("/check")
def inspect_domain(
    domain: str = Query(..., description="Domain name to inspect e.g. talentops.ai"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_request),
):
    """
    Forensically inspects a domain for SPF, DKIM, DMARC, MX, and DNS reputation.
    Returns composite deliverability health score (0-100) and actionable remediation steps.
    """
    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Invalid domain format")
    
    clean_domain = domain.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    result = check_domain_health(clean_domain)
    return result

@router.get("/warmup-schedule")
def domain_warmup_schedule(
    user: User = Depends(get_current_user_from_request),
):
    """
    Returns the recommended 4-week ramp-up schedule for new cold outbound sending domains.
    """
    return get_warmup_schedule()
