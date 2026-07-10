import sys
import os
import argparse
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

# Setup path and imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Company, Recruiter, Submission, Candidate, RecruiterPhone, RecruiterLocation, RecruiterEmail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("night_sweeper")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def deduplicate_companies(db: Session, dry_run: bool):
    logger.info("Starting Company Deduplication...")
    
    # Find companies with exact same website
    # Exclude null or empty websites
    duplicate_groups = db.execute(text("""
        SELECT website, array_agg(company_id ORDER BY company_id ASC) as ids
        FROM companies
        WHERE website IS NOT NULL AND website != '' AND is_active = true
        GROUP BY website
        HAVING COUNT(company_id) > 1
    """)).mappings().all()

    total_merged = 0
    for group in duplicate_groups:
        ids = group['ids']
        golden_id = ids[0]
        duplicate_ids = ids[1:]
        
        if dry_run:
            logger.info(f"[DRY RUN] Would merge {len(duplicate_ids)} duplicates into Company #{golden_id} (website: {group['website']})")
        else:
            logger.info(f"Merging {len(duplicate_ids)} duplicates into Company #{golden_id} (website: {group['website']})")
            
            # 1. Update Recruiters
            db.execute(text("UPDATE recruiters SET company_id = :golden_id WHERE company_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
            
            # 2. Update Submissions
            db.execute(text("UPDATE submissions SET company_id = :golden_id WHERE company_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
            
            # 3. Update Recruiter Phones
            db.execute(text("UPDATE recruiter_phones SET company_id = :golden_id WHERE company_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
                       
            # 4. Update Recruiter Locations
            db.execute(text("UPDATE recruiter_locations SET company_id = :golden_id WHERE company_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})

            # 5. Deactivate duplicates (DO NOT DELETE)
            for dup_id in duplicate_ids:
                dup_comp = db.query(Company).get(dup_id)
                if dup_comp:
                    dup_comp.is_active = False
                    current_notes = dup_comp.notes or ""
                    dup_comp.notes = f"[NIGHT_SWEEPER] Merged into company_id: {golden_id}. " + current_notes
            if total_merged % 250 == 0:
                db.commit()
            
        total_merged += len(duplicate_ids)

    if not dry_run:
        db.commit()
    logger.info(f"Finished Company Deduplication. Merged {total_merged} companies.")



def deduplicate_recruiters(db: Session, dry_run: bool):
    logger.info("Starting Recruiter Deduplication...")
    
    # Find recruiters with exact same normalized_recruiter_name and company_id
    # Exclude nulls
    duplicate_groups = db.execute(text("""
        SELECT normalized_recruiter_name, company_id, array_agg(recruiter_id ORDER BY recruiter_id ASC) as ids
        FROM recruiters
        WHERE normalized_recruiter_name IS NOT NULL AND normalized_recruiter_name != '' 
          AND company_id IS NOT NULL 
          AND is_active = true
        GROUP BY normalized_recruiter_name, company_id
        HAVING COUNT(recruiter_id) > 1
    """)).mappings().all()

    total_merged = 0
    for group in duplicate_groups:
        ids = group['ids']
        
        # Golden record is the one with the most completeness_score (or just oldest if tied)
        recs = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(ids)).order_by(Recruiter.completeness_score.desc(), Recruiter.recruiter_id.asc()).all()
        if not recs: continue
        
        golden_rec = recs[0]
        golden_id = golden_rec.recruiter_id
        duplicate_ids = [r.recruiter_id for r in recs[1:]]
        
        if dry_run:
            logger.info(f"[DRY RUN] Would merge {len(duplicate_ids)} duplicates into Recruiter #{golden_id} (name: {group['normalized_recruiter_name']})")
        else:
            logger.info(f"Merging {len(duplicate_ids)} duplicates into Recruiter #{golden_id} (name: {group['normalized_recruiter_name']})")
            
            for dup_rec in recs[1:]:
                # Merge missing fields into golden record
                if not golden_rec.phone and dup_rec.phone: golden_rec.phone = dup_rec.phone
                if not golden_rec.linkedin and dup_rec.linkedin: golden_rec.linkedin = dup_rec.linkedin
                if not golden_rec.specialization and dup_rec.specialization: golden_rec.specialization = dup_rec.specialization
                if not golden_rec.title and dup_rec.title: golden_rec.title = dup_rec.title
                if not golden_rec.location and dup_rec.location: golden_rec.location = dup_rec.location
                if not golden_rec.company_id and dup_rec.company_id: golden_rec.company_id = dup_rec.company_id
                
                # Combine notes
                if dup_rec.notes:
                    current_notes = golden_rec.notes or ""
                    golden_rec.notes = current_notes + f" | Notes from {dup_rec.recruiter_id}: {dup_rec.notes}"
                
                # Deactivate duplicate (DO NOT DELETE)
                dup_rec.is_active = False
                dup_notes = dup_rec.notes or ""
                dup_rec.notes = f"[NIGHT_SWEEPER] Merged into recruiter_id: {golden_id}. " + dup_notes
            
            # 1. Update Candidates
            db.execute(text("UPDATE candidates SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
            
            # 2. Update Submissions
            db.execute(text("UPDATE submissions SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})

            # 3. Update Recruiter Emails
            db.execute(text("UPDATE recruiter_emails SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})

            # 4. Update Recruiter Phones
            db.execute(text("UPDATE recruiter_phones SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
                       
            # 5. Update Recruiter Locations
            db.execute(text("UPDATE recruiter_locations SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})
                       
            # 6. Update Enrichment Audits
            db.execute(text("UPDATE enrichment_audit SET recruiter_id = :golden_id WHERE recruiter_id = ANY(:duplicate_ids)"), 
                       {"golden_id": golden_id, "duplicate_ids": duplicate_ids})

            if total_merged % 250 == 0:
                db.commit()
            
        total_merged += len(duplicate_ids)

    if not dry_run:
        db.commit()
    logger.info(f"Finished Recruiter Deduplication. Merged {total_merged} recruiters.")


def main():

    parser = argparse.ArgumentParser(description="Autonomous Night Sweeper for Database Deduplication")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes to DB")
    args = parser.parse_args()

    db = next(get_db())
    
    if args.dry_run:
        logger.info("=== STARTING NIGHT SWEEPER (DRY RUN MODE) ===")
    else:
        logger.info("=== STARTING NIGHT SWEEPER (LIVE EXECUTION) ===")

    deduplicate_companies(db, args.dry_run)
    deduplicate_recruiters(db, args.dry_run)
    
    logger.info("=== NIGHT SWEEPER COMPLETE ===")

if __name__ == "__main__":
    main()
