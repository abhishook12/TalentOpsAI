"""
campaign_priority_intelligence.py
========================================================================================
API Endpoints for Campaign Priority Leadership & Cross-Entity Validation Engine
========================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from ..database import get_db
from ..services.campaign_priority_intelligence_service import campaign_priority_service
from ..models.models import Recruiter, Company

router = APIRouter(prefix="/api/campaigns/priority-intelligence", tags=["Campaign Priority Intelligence"])


@router.post("/sync", response_model=Dict[str, Any])
def sync_priority_intelligence():
    """Triggers the full autonomous campaign priority leadership & cross-entity validation cycle."""
    result = campaign_priority_service.run_full_cycle()
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
    return result


@router.get("/summary", response_model=Dict[str, Any])
def get_priority_intelligence_summary(db: Session = Depends(get_db)):
    """Returns real-time metrics on campaign priority stakeholders and enriched companies."""
    total_priority_recs = db.query(Recruiter).filter(Recruiter.is_priority_contact == True).count()
    decision_makers = db.query(Recruiter).filter(Recruiter.priority_tier == "TOP_DECISION_MAKER").count()
    campaign_active = db.query(Recruiter).filter(Recruiter.priority_tier == "CAMPAIGN_ACTIVE").count()
    tracked_comps = db.query(Company).filter(Company.is_tracked == True).count()

    return {
        "status": "SUCCESS",
        "telemetry": campaign_priority_service.telemetry,
        "counts": {
            "total_priority_contacts": total_priority_recs,
            "top_decision_makers": decision_makers,
            "campaign_active_contacts": campaign_active,
            "tracked_companies_with_roster": tracked_comps
        }
    }


@router.get("/company/{company_id}/leaders", response_model=Dict[str, Any])
def get_company_priority_leaders(company_id: int, db: Session = Depends(get_db)):
    """Retrieves the verified active campaign leadership roster for a specific company."""
    comp = db.query(Company).filter(Company.company_id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company not found")

    leaders = []
    if comp.metadata_json:
        import json
        try:
            meta = json.loads(comp.metadata_json)
            leaders = meta.get("key_priority_leaders", [])
        except Exception:
            leaders = []

    if not leaders:
        # Fallback query
        recs = db.query(Recruiter).filter(
            Recruiter.company_id == company_id,
            Recruiter.is_priority_contact == True
        ).all()
        leaders = [{
            "recruiter_id": r.recruiter_id,
            "name": r.recruiter_name,
            "title": r.title,
            "email": r.email,
            "phone": r.phone,
            "linkedin": r.linkedin,
            "priority_tier": r.priority_tier,
            "campaign_sent_count": r.campaign_sent_count or 0
        } for r in recs]

    return {
        "company_id": comp.company_id,
        "company_name": comp.company_name,
        "primary_domain": comp.primary_domain,
        "is_tracked": comp.is_tracked,
        "total_leaders": len(leaders),
        "key_priority_leaders": leaders
    }
