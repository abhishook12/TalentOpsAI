import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company, DomainIntelligence, EnrichmentAudit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sentinel_phase2")

FREEMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "msn.com", "live.com"}

def calculate_completeness_score(r: Recruiter, c: Company):
    """Rule 9: Recruiter Completeness Score across 15 fields"""
    score = 0
    total_fields = 15
    missing = []

    fields = [
        ("Name", r.recruiter_name),
        ("Company", c.company_name if c else None),
        ("Title", r.title),
        ("Primary email", r.email),
        ("Secondary email", r.email2),
        ("Phone", r.phone),
        ("LinkedIn", r.linkedin),
        ("City", r.normalized_city),
        ("State", r.state),
        ("Country", r.location), # using location as fallback/proxy for now
        ("Skills", r.tags),
        ("Department", r.taxonomy_category),
        ("Specialization", r.specialization),
        ("Company logo", None), # Will be checked later via DomainIntelligence
        ("Company website", c.website if c else None)
    ]
    
    for fname, val in fields:
        if val and str(val).strip() and "missing.local" not in str(val).lower():
            score += 1
        else:
            missing.append(fname)
            
    # Calculate percentage
    pct = int((score / total_fields) * 100)
    return pct, missing

def extract_domain(email: str):
    if not email or "@" not in email:
        return None
    domain = email.split("@")[1].strip().lower()
    return domain

def infer_company_from_domain(db, domain: str, recruiter: Recruiter):
    """Rule 2, 3, 7: Company Intelligence & Domain Intelligence"""
    if domain in FREEMAIL_DOMAINS:
        return None, 0, "Personal email domain (freemail)"
        
    # Check DomainIntelligence
    di = db.query(DomainIntelligence).filter(DomainIntelligence.domain == domain).first()
    if not di:
        # Create it (Continuous Learning)
        di = DomainIntelligence(
            domain=domain,
            is_personal=False,
            confidence_score=50,
            evidence=json.dumps({"source": "Extracted from recruiter email", "recruiter_id": recruiter.recruiter_id})
        )
        db.add(di)
        db.flush()

    if di.company_id:
        # We already mapped this domain to a company
        return di.company_id, di.confidence_score, f"Inferred from DomainIntelligence mapping for {domain}"
        
    # Attempt to find Company by website or exact name (Rule 8 Deduplication)
    c = db.query(Company).filter(
        (Company.website.ilike(f"%{domain}%")) | 
        (Company.email_pattern == domain)
    ).order_by(Company.trust_score.desc()).first()
    
    if c:
        # We found a canonical company
        di.company_id = c.company_id
        di.company_name = c.company_name
        di.confidence_score = 90
        di.evidence = json.dumps({"source": "Matched existing canonical company", "company_id": c.company_id})
        
        # Rule 8: If there are other companies with this domain, they are duplicates. We could merge them later, 
        # but for now we just assign this recruiter to the canonical one.
        
        db.flush()
        return c.company_id, 90, f"Matched existing company ({domain})"
        
    # If no company, create one?
    # For now, we will create a placeholder company derived from the domain
    new_company_name = domain.split('.')[0].capitalize()
    new_comp = Company(
        company_name=new_company_name,
        website=f"https://www.{domain}",
        email_pattern=domain,
        data_source="sentinel_inference",
        trust_score=80
    )
    db.add(new_comp)
    db.flush()
    
    di.company_id = new_comp.company_id
    di.company_name = new_company_name
    di.confidence_score = 80
    di.evidence = json.dumps({"source": "Auto-created from domain", "company_id": new_comp.company_id})
    db.flush()
    
    return new_comp.company_id, 80, f"Auto-created company '{new_company_name}' from domain {domain}"


def process_batch(batch_size=50):
    db = SessionLocal()
    try:
        # Fetch Pending recruiters
        recruiters = db.query(Recruiter).filter(
            Recruiter.sentinel_status.in_(["Pending", "Analyzing"])
        ).limit(batch_size).all()
        
        if not recruiters:
            return 0
            
        processed = 0
        for r in recruiters:
            try:
                r.sentinel_status = "Analyzing"
                db.flush()
                
                # Rule 2, 3, 7: Company Inference
                old_company_id = r.company_id
                if not r.company_id and r.email:
                    domain = extract_domain(r.email)
                    if domain:
                        comp_id, conf, reason = infer_company_from_domain(db, domain, r)
                        if comp_id:
                            r.company_id = comp_id
                            r.company_confidence = conf
                            r.company_reasoning = reason
                            
                            # Log Audit
                            audit = EnrichmentAudit(
                                recruiter_id=r.recruiter_id,
                                enrichment_type="company_inference",
                                original_value=str(old_company_id),
                                proposed_value=str(comp_id),
                                final_value=str(comp_id),
                                source="Sentinel Phase II",
                                confidence_score=conf,
                                action="assigned",
                                reason=reason,
                                run_id="sentinel_phase_2"
                            )
                            db.add(audit)
                
                # Reload company relation
                db.refresh(r)
                c = r.company
                
                # Rule 9: Completeness
                score, missing = calculate_completeness_score(r, c)
                r.completeness_score = score
                r.missing_fields = json.dumps(missing)
                
                # Rule 14: Manual Review Queue
                if r.company_confidence and r.company_confidence < 70:
                    r.needs_review = True
                    r.review_reason = f"Low confidence company match ({r.company_confidence}%): {r.company_reasoning}"
                
                r.sentinel_status = "Completed"
                r.last_verified_at = datetime.now(timezone.utc)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing recruiter {r.recruiter_id}: {e}")
                r.sentinel_status = "Error"
                
        db.commit()
        return processed
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting SENTINEL Phase II Worker...")
    batch_size = 50
    consecutive_empty = 0
    
    while True:
        try:
            count = process_batch(batch_size)
            if count > 0:
                logger.info(f"Processed batch of {count} profiles.")
                consecutive_empty = 0
                time.sleep(0.5)
            else:
                consecutive_empty += 1
                if consecutive_empty % 10 == 0:
                    logger.info("No profiles to process. Sleeping...")
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Engine stopped by user.")
            break
        except Exception as e:
            logger.error(f"Engine exception: {e}")
            time.sleep(10)
