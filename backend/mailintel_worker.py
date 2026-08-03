import os
import sys
import time
import json
import logging
from datetime import datetime, timezone
import dns.resolver
from email_validator import validate_email, EmailNotValidError

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import RecruiterEmail, MailIntelEvidence, MailIntelTracking, Company, Recruiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Basic domains that are likely personal/freemail
FREEMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com"}

def check_mx(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except Exception:
        return False

def verify_email_record(db, email_record):
    start_time = time.time()
    evidence_collected = {}
    confidence = 0
    method = []
    
    raw_email = email_record.email.lower().strip() if email_record.email else ""
    
    # 1. Syntax Check
    syntax_valid = False
    try:
        valid = validate_email(raw_email, check_deliverability=False)
        raw_email = valid.normalized
        domain = raw_email.split('@')[1]
        syntax_valid = True
        confidence += 20
        evidence_collected["syntax"] = {"valid": True, "normalized": raw_email}
        method.append("Syntax")
    except EmailNotValidError as e:
        evidence_collected["syntax"] = {"valid": False, "error": str(e)}
        domain = ""
        method.append("Syntax")

    if syntax_valid:
        # 2. Domain MX Check
        has_mx = check_mx(domain)
        evidence_collected["mx_record"] = {"has_mx": has_mx}
        method.append("Domain")
        if has_mx:
            confidence += 30
        else:
            confidence -= 20
            
        # 3. Company Consistency
        # Get the company via recruiter
        recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == email_record.recruiter_id).first()
        company_domain_match = False
        if recruiter and recruiter.company_id:
            company = db.query(Company).filter(Company.company_id == recruiter.company_id).first()
            if company and company.website:
                # Extract domain from website (e.g., https://www.example.com -> example.com)
                company_domain = company.website.lower().replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                company_domain_clean = company_domain
                
                if company_domain_clean == domain or f".{company_domain_clean}" in domain:
                    company_domain_match = True
                    confidence += 20
                elif domain in FREEMAIL_DOMAINS:
                    evidence_collected["company_match"] = {"match": False, "reason": "freemail"}
                    # No penalty for freemail, just no bonus
                else:
                    evidence_collected["company_match"] = {"match": False, "expected": company_domain_clean, "found": domain}
                    confidence -= 10
        
        if company_domain_match:
            evidence_collected["company_match"] = {"match": True}
        method.append("Consistency")

        # 4. Historical Intelligence
        tracking = db.query(MailIntelTracking).filter(MailIntelTracking.email_id == email_record.id).first()
        if tracking:
            history_evidence = {
                "delivered": bool(tracking.last_delivery_at),
                "replied": bool(tracking.last_reply_at),
                "hard_bounces": tracking.hard_bounce_count,
                "soft_bounces": tracking.soft_bounce_count
            }
            if tracking.last_delivery_at:
                confidence += 20
            if tracking.last_reply_at:
                confidence += 20  # Huge signal
            if tracking.hard_bounce_count > 0:
                confidence -= 50
            evidence_collected["historical"] = history_evidence
            method.append("Historical")
            
        # 5. Duplicate Detection
        duplicate_count = db.query(RecruiterEmail).filter(RecruiterEmail.email == raw_email, RecruiterEmail.id != email_record.id).count()
        if duplicate_count > 1:
            evidence_collected["duplicates"] = {"count": duplicate_count}
            confidence -= 15  # Suspect if shared heavily
            method.append("DuplicateCheck")

    # Bound confidence
    confidence = max(0, min(100, confidence))
    
    # Calculate duration
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Assign Status
    status = "unknown"
    if confidence >= 90:
        status = "verified"
    elif confidence >= 70:
        status = "likely_valid"
    elif confidence >= 40:
        status = "needs_monitoring"
    elif confidence >= 1:
        status = "suspicious"
    else:
        status = "invalid"

    # Update record
    confidence_delta = confidence - (email_record.confidence_score or 0)
    email_record.confidence_score = confidence
    email_record.status = status
    email_record.last_checked_at = datetime.now(timezone.utc)

    # We determine version by counting existing evidence or just default to 1 for now (could be optimized)
    version = db.query(MailIntelEvidence).filter(MailIntelEvidence.email_id == email_record.id).count() + 1

    # Record Evidence
    evidence = MailIntelEvidence(
        email_id=email_record.id,
        method=",".join(method),
        evidence_json=evidence_collected,
        confidence_delta=confidence_delta,
        final_confidence=confidence,
        duration_ms=duration_ms,
        verification_version=version
    )
    db.add(evidence)
    
    return confidence, status, duration_ms

def process_batch(batch_size=50):
    db = SessionLocal()
    try:
        # Fetch oldest checked emails (or never checked)
        # Using NULLS FIRST is natively supported in Postgres via nullsfirst()
        from sqlalchemy import nullsfirst
        emails = db.query(RecruiterEmail).order_by(nullsfirst(RecruiterEmail.last_checked_at.asc())).limit(batch_size).all()
        
        if not emails:
            return 0
            
        processed = 0
        for email_record in emails:
            try:
                verify_email_record(db, email_record)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing email ID {email_record.id}: {e}")
                
        db.commit()
        return processed
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting MAILINTEL Background Verification Engine...")
    batch_size = 50
    consecutive_empty = 0
    
    while True:
        try:
            count = process_batch(batch_size)
            if count > 0:
                logger.info(f"Processed batch of {count} emails.")
                consecutive_empty = 0
                time.sleep(0.5) # Throttle to prevent DNS bans and DB overload
            else:
                consecutive_empty += 1
                logger.info("No emails to process. Sleeping...")
                time.sleep(60) # Sleep longer if queue is empty
        except KeyboardInterrupt:
            logger.info("Engine stopped by user.")
            break
        except Exception as e:
            logger.error(f"Engine exception: {e}")
            time.sleep(10)
