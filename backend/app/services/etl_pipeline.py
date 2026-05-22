import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models.models import StagingRecruiter, Recruiter, Company, StagingCompany
from app.utils.normalizer import normalize_text, extract_domain
from app.utils.state_mapper import normalize_state

logger = logging.getLogger(__name__)

def process_staging_records():
    """
    Background job to pull from Staging tables, normalize, deduplicate, 
    calculate confidence scores, and insert into Approved tables.
    """
    db: Session = SessionLocal()
    try:
        # Process Staging Companies first
        staging_comps = db.query(StagingCompany).filter(StagingCompany.status == "pending").limit(500).all()
        for s_comp in staging_comps:
            norm_name = normalize_text(s_comp.company_name)
            
            # Deduplicate
            existing = db.query(Company).filter(Company.normalized_company_name == norm_name).first()
            if existing:
                s_comp.status = "duplicate"
            else:
                new_comp = Company(
                    company_name=s_comp.company_name,
                    normalized_company_name=norm_name,
                    location=s_comp.location,
                    industry=s_comp.industry,
                    data_source="etl",
                    trust_score=80
                )
                db.add(new_comp)
                s_comp.status = "approved"
        db.commit()

        # Process Staging Recruiters
        staging_recs = db.query(StagingRecruiter).filter(StagingRecruiter.status == "pending").limit(1000).all()
        
        # Prefetch existing emails for quick lookup
        emails_in_batch = [r.email for r in staging_recs if r.email]
        existing_emails = set()
        if emails_in_batch:
            rows = db.query(Recruiter.email).filter(Recruiter.email.in_(emails_in_batch)).all()
            existing_emails = {r.email for r in rows}

        for s_rec in staging_recs:
            if not s_rec.email or s_rec.email in existing_emails:
                s_rec.status = "duplicate"
                continue

            # Company linking
            company_id = None
            if s_rec.company_name:
                norm_comp = normalize_text(s_rec.company_name)
                comp = db.query(Company).filter(Company.normalized_company_name == norm_comp).first()
                if comp:
                    company_id = comp.company_id
            
            # If no company found by name, try domain extraction
            if not company_id and s_rec.email:
                domain = extract_domain(s_rec.email)
                if domain and domain not in ('gmail.com', 'yahoo.com', 'hotmail.com'):
                    # Trigram search for company by domain
                    sql = text("""
                        SELECT company_id 
                        FROM companies 
                        WHERE website ILIKE '%' || :domain || '%' 
                        OR email_pattern ILIKE '%' || :domain || '%'
                        LIMIT 1
                    """)
                    res = db.execute(sql, {"domain": domain}).first()
                    if res:
                        company_id = res.company_id

            # Calculate confidence score
            score = 50 # Base score
            if s_rec.phone: score += 20
            if company_id: score += 20
            if s_rec.location: score += 10

            new_rec = Recruiter(
                recruiter_name=s_rec.recruiter_name,
                normalized_recruiter_name=normalize_text(s_rec.recruiter_name),
                email=s_rec.email,
                phone=s_rec.phone,
                company_id=company_id,
                location=s_rec.location,
                state=normalize_state(s_rec.location) if s_rec.location else None,
                completeness_score=score,
                data_source="etl",
                trust_score=score,
                needs_review=(score < 60)
            )
            db.add(new_rec)
            existing_emails.add(s_rec.email)
            s_rec.status = "approved"

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"ETL Pipeline Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    process_staging_records()
