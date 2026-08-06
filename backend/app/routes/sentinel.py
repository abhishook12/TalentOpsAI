from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.database import get_db
from app.models.models import Recruiter, Company, DomainIntelligence, EnrichmentAudit

router = APIRouter(prefix="/sentinel", tags=["Sentinel Engine"])

@router.get("/stats")
def get_sentinel_stats(db: Session = Depends(get_db)):
    """Rule 13: Data Intelligence Dashboard Metrics"""
    total_processed = db.query(Recruiter).filter(Recruiter.sentinel_status == "Completed").count()
    total_queued = db.query(Recruiter).filter(Recruiter.sentinel_status.in_(["Pending", "Analyzing"])).count()
    companies_identified = db.query(Recruiter).filter(Recruiter.company_id.isnot(None)).count()
    unknown_companies = db.query(Recruiter).filter(Recruiter.company_id.is_(None)).count()
    domains_mapped = db.query(DomainIntelligence).count()
    
    # Enrichment counts (from audit log)
    profiles_enriched = db.query(EnrichmentAudit.recruiter_id).distinct().count()
    
    return {
        "total_processed": total_processed,
        "total_queued": total_queued,
        "companies_identified": companies_identified,
        "unknown_companies": unknown_companies,
        "domains_mapped": domains_mapped,
        "profiles_enriched": profiles_enriched,
        "duplicate_companies_merged": 0  # To be implemented
    }

@router.get("/review-queue")
def get_review_queue(
    db: Session = Depends(get_db),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Rule 14: Manual Review Queue for low confidence company matches"""
    query = db.query(Recruiter).filter(Recruiter.needs_review == True)
    total = query.count()
    
    items = query.order_by(Recruiter.updated_at.desc()).limit(limit).offset(offset).all()
    
    results = []
    for r in items:
        company_data = None
        if r.company:
            company_data = {
                "company_id": r.company.company_id,
                "company_name": r.company.company_name,
                "website": r.company.website
            }
            
        results.append({
            "recruiter_id": r.recruiter_id,
            "recruiter_name": r.recruiter_name,
            "email": r.email,
            "company_confidence": r.company_confidence,
            "review_reason": r.review_reason,
            "suggested_company": company_data
        })
        
    return {
        "items": results,
        "total": total
    }

@router.post("/review-queue/{recruiter_id}/approve")
def approve_review(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    r.needs_review = False
    r.review_reason = None
    r.company_confidence = 100
    
    audit = EnrichmentAudit(
        recruiter_id=r.recruiter_id,
        enrichment_type="company_review",
        action="approved",
        reason="Manual admin approval of suggested company",
        run_id="manual_review"
    )
    db.add(audit)
    db.commit()
    return {"status": "success"}

@router.post("/review-queue/{recruiter_id}/reject")
def reject_review(recruiter_id: int, db: Session = Depends(get_db)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    old_company = r.company_id
    r.needs_review = False
    r.review_reason = None
    r.company_id = None
    r.company_confidence = 0
    
    audit = EnrichmentAudit(
        recruiter_id=r.recruiter_id,
        enrichment_type="company_review",
        action="rejected",
        reason="Manual admin rejection of suggested company",
        original_value=str(old_company),
        proposed_value="None",
        run_id="manual_review"
    )
    db.add(audit)
    db.commit()
    return {"status": "success"}
