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
        
        for i, part in enumerate(parts):
            part_lower = part.lower()
            if len(part) > 3 and "linkedin" not in part_lower and name.lower() not in part_lower and company.lower() not in part_lower:
                if ',' in part and len(part) < 30:
                    location = part
                elif not title and len(part) < 60:
                    title = part
                    
        return title, location

    def enrich_recruiter_sync(self, db: Session, recruiter: Recruiter):
        """
        Synchronous JIT Enrichment.
        Takes an ORM recruiter model, performs a DDG search, and updates missing data.
        Returns True if enriched, False otherwise.
        """
        if recruiter.linkedin and recruiter.title and recruiter.location:
            return False

        if not recruiter.recruiter_name or not recruiter.company_id:
            return False
            
        company = db.query(Company).filter(Company.company_id == recruiter.company_id).first()
        company_name = company.company_name if company else ""
        
        if not company_name:
            return False

        query = f'site:linkedin.com/in/ "{recruiter.recruiter_name}" "{company_name}"'
        
        try:
            results = list(self.ddgs.text(query, max_results=3))
            
            for res in results:
                href = res.get('href', '')
                if 'linkedin.com/in/' in href:
                    updated = False
                    
                    if not recruiter.linkedin:
                        recruiter.linkedin = href
                        updated = True
                        
                    combined_text = res.get('title', '') + " - " + res.get('body', '')
                    title, location = self._extract_title_location_from_snippet(combined_text, recruiter.recruiter_name, company_name)
                    
                    if not recruiter.title and title:
                        recruiter.title = title
                        updated = True
                        
                    if not recruiter.location and location:
                        recruiter.location = location
                        updated = True
                        
                    if updated:
                        db.commit()
                        logger.info(f"JIT Enriched Recruiter {recruiter.recruiter_id}: {title} | {location} | {href}")
                        return True
                        
            return False
        except Exception as e:
            logger.error(f"Error in JIT enrichment for {recruiter.recruiter_id}: {e}")
            return False

jit_enrichment_service = JITEnrichmentService()
