import re
from duckduckgo_search import DDGS
import logging
from sqlalchemy.orm import Session
from app.models.models import Recruiter, Company

logger = logging.getLogger(__name__)

class JITEnrichmentService:
    def __init__(self):
        self.ddgs = DDGS()

    def _extract_title_location_from_snippet(self, text, name, company):
        parts = [p.strip() for p in text.split('-')]
        title = None
        location = None
        phone = None
        
        # Look for phone numbers in the snippet
        phone_matches = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_matches:
            phone = phone_matches[0]
            
        for i, part in enumerate(parts):
            part_lower = part.lower()
            if len(part) > 3 and "linkedin" not in part_lower and name.lower() not in part_lower and company.lower() not in part_lower:
                if ',' in part and len(part) < 30:
                    location = part
                elif not title and len(part) < 60:
                    title = part
                    
        return title, location, phone

    def enrich_recruiter_sync(self, db: Session, recruiter: Recruiter):
        """
        Synchronous JIT Enrichment using Tavily API.
        Returns True if enriched, False otherwise.
        """
        if recruiter.email and recruiter.phone and recruiter.location:
            return False

        if not recruiter.recruiter_name or not recruiter.company_id:
            return False
            
        company = db.query(Company).filter(Company.company_id == recruiter.company_id).first()
        company_name = company.company_name if company else ""
        company_domain = company.website if company else ""
        
        if not company_name:
            return False

        try:
            from app.services.scraper import auto_enhance_recruiter_data
            result = auto_enhance_recruiter_data(recruiter.recruiter_name, company_name, company_domain)
            
            updated = False
            
            if result.get('phone') and not recruiter.phone:
                recruiter.phone = result['phone']
                updated = True
                
            if result.get('phone') and not recruiter.phone2:
                recruiter.phone2 = result['phone']
                updated = True
                
            if result.get('email') and not recruiter.email:
                recruiter.email = result['email']
                updated = True
                
            if result.get('location') and not recruiter.location:
                recruiter.location = result['location']
                updated = True
                
            if updated:
                db.commit()
                logger.info(f"Tavily Enriched Recruiter {recruiter.recruiter_id}: Phone: {result.get('phone')} | Location: {result.get('location')}")
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error in JIT enrichment for {recruiter.recruiter_id}: {e}")
            return False

jit_enrichment_service = JITEnrichmentService()
