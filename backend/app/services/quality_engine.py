import threading
import time
import logging
import duckdb
import json
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import SessionLocal, engine
from ..models.models import Recruiter, Company, RepairLog
from ..services.parquet_writer import parquet_writer
from ..services.recruiter_store import recruiter_store

logger = logging.getLogger(__name__)

class QualityEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self.parquet_path = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info("QualityEngine started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("QualityEngine stopped.")

    def _run_loop(self):
        while self.running:
            try:
                self.run_vulnerability_scan()
                self.process_safe_repairs()
            except Exception as e:
                logger.error(f"Error in QualityEngine loop: {e}")
            time.sleep(60) # Run every 60 seconds

    def run_vulnerability_scan(self):
        """Phase 2: Vulnerability Scan. Flags records missing crucial fields."""
        db = SessionLocal()
        try:
            # Postgres check for missing fields
            # Tier 1: Tracked companies that haven't been scanned
            companies = db.query(Company).filter(
                Company.quality_flags.is_(None),
                Company.is_tracked == True
            ).limit(500).all()
            
            if len(companies) < 500:
                # Tier 2: Remaining unscanned companies
                more_companies = db.query(Company).filter(
                    Company.quality_flags.is_(None),
                    or_(Company.is_tracked == False, Company.is_tracked.is_(None))
                ).limit(500 - len(companies)).all()
                companies.extend(more_companies)
                
            for company in companies:
                flags = []
                if not company.website:
                    flags.append("missing_website")
                if not company.location or company.location.lower() in ('unknown', 'n/a'):
                    flags.append("missing_location")
                if not company.industry:
                    flags.append("missing_industry")
                if not company.linkedin_url:
                    flags.append("missing_linkedin")
                
                # Check for "Unknown" names
                if company.company_name and company.company_name.lower() in ('unknown', 'n/a', 'none'):
                    flags.append("unknown_name")
                    
                company.quality_flags = json.dumps(flags)
                
                # Base score 100
                score = 100
                if 'missing_website' in flags: score -= 25
                if 'missing_location' in flags: score -= 25
                if 'unknown_name' in flags: score -= 50
                if 'missing_industry' in flags: score -= 10
                if 'missing_linkedin' in flags: score -= 10
                
                company.completeness_score = max(0, score)
                
            db.commit()
            
            # Recruiters are served from Parquet, not the legacy Postgres table.
            # Writing quality values to Postgres here made the dashboard stale.
            recruiter_store._ensure_loaded()
            recruiter_rows = recruiter_store._conn.cursor().execute("""
                SELECT recruiter_id, location, linkedin, title, phone
                FROM recruiters
                WHERE quality_flags IS NULL OR quality_flags = ''
                LIMIT 5000
            """).fetchdf()
            recruiter_updates = []
            for _, r in recruiter_rows.iterrows():
                flags = []
                if not r.get('location'):
                    flags.append("missing_location")
                if not r.get('linkedin'):
                    flags.append("missing_linkedin")
                if not r.get('title'):
                    flags.append("missing_title")
                if not r.get('phone'):
                    flags.append("missing_phone")
                score = 100
                if 'missing_location' in flags: score -= 30
                if 'missing_linkedin' in flags: score -= 30
                if 'missing_title' in flags: score -= 20
                if 'missing_phone' in flags: score -= 20
                recruiter_updates.append({
                    'recruiter_id': int(r['recruiter_id']),
                    'quality_flags': json.dumps(flags),
                    'completeness_score': max(0, score),
                })

            if recruiter_updates:
                parquet_writer.update_records(recruiter_updates)
            
        finally:
            db.close()

    def process_safe_repairs(self):
        """Phase 4: Safe Repairs using RepairLog.
        For now, this is a placeholder for automatic corrections.
        For instance, fixing common casing issues in names or normalizing locations.
        """
        db = SessionLocal()
        try:
            recruiter_store._ensure_loaded()
            recruiters = recruiter_store._conn.cursor().execute("""
                SELECT recruiter_id, recruiter_name
                FROM recruiters
                WHERE recruiter_name IS NOT NULL AND recruiter_name = LOWER(recruiter_name)
                LIMIT 1000
            """).fetchdf()
            updates = []
            for _, r in recruiters.iterrows():
                if r['recruiter_name']:
                    old_val = r['recruiter_name']
                    new_val = old_val.title()
                    updates.append({'recruiter_id': int(r['recruiter_id']), 'recruiter_name': new_val})
                    repair_log = RepairLog(
                        entity_type='Recruiter',
                        entity_id=int(r['recruiter_id']),
                        field_name='recruiter_name',
                        old_value=old_val,
                        new_value=new_val,
                        confidence=95,
                        evidence='Auto-capitalized lowercase name',
                        source='QualityEngine'
                    )
                    db.add(repair_log)
            if updates:
                parquet_writer.update_records(updates)
            db.commit()
        except Exception as e:
            logger.error(f"Error in process_safe_repairs: {e}")
        finally:
            db.close()
        
quality_engine = QualityEngine()
