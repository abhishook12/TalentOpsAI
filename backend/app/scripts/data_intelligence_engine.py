import os
import sys
import argparse
import re
from datetime import datetime
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

STATE_ABBR = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS', 'MISSOURI': 'MO',
    'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ',
    'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
    'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT',
    'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'
}

def infer_state(loc_text):
    if not loc_text: return None, None, None
    loc_text = loc_text.upper()
    
    # Direct abbreviation format like "Austin, TX"
    match = re.search(r'\b([A-Z]{2})\b', loc_text)
    if match and match.group(1) in STATE_ABBR.values():
        return match.group(1), 'high', f'Found direct abbreviation {match.group(1)} in location string'
        
    # Full name format
    for full_name, abbr in STATE_ABBR.items():
        if full_name in loc_text:
            return abbr, 'high', f'Found full state name {full_name} in location string'
            
    return None, None, None

def run_engine(dry_run=True, batch_size=1000):
    db = SessionLocal()
    print(f"--- STARTING DATA INTELLIGENCE ENGINE V2 ---")
    if dry_run:
        print(f"!!! DRY RUN MODE ACTIVE - NO CHANGES WILL BE SAVED !!!\n")
    else:
        print(f"!!! LIVE EXECUTION MODE ACTIVE (Batch Size: {batch_size}) !!!\n")

    # 1. Flag Duplicate Phones
    print("Finding shared phone numbers...")
    dup_phones = db.execute(text("SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' GROUP BY phone HAVING COUNT(*) > 1")).fetchall()
    dup_phone_set = {p[0] for p in dup_phones}
    print(f"Found {len(dup_phone_set)} phone numbers shared across multiple recruiters.")

    # 2. Flag Duplicate Name/Company
    print("Finding shared Name + Company combinations...")
    dup_nc = db.execute(text("SELECT recruiter_name, company_id FROM recruiters WHERE recruiter_name != 'Unknown' AND company_id IS NOT NULL GROUP BY recruiter_name, company_id HAVING COUNT(*) > 1")).fetchall()
    dup_nc_set = {(r[0], r[1]) for r in dup_nc}
    print(f"Found {len(dup_nc_set)} shared Name+Company combinations.")

    total_recruiters = db.query(Recruiter).count()
    print(f"Total recruiters to process: {total_recruiters}")

    updates = 0
    inferred_states = 0
    flagged_reviews = 0
    normalized_names = 0
    processed = 0

    scan_time = datetime.utcnow()

    # Process in batches to avoid locking
    for offset in range(0, total_recruiters, batch_size):
        recruiters = db.query(Recruiter).order_by(Recruiter.recruiter_id).offset(offset).limit(batch_size).all()
        for r in recruiters:
            needs_update = False
            review_reasons = []

            # Name Normalization
            if r.recruiter_name and r.recruiter_name != 'Unknown' and r.recruiter_name != r.recruiter_name.title():
                r.recruiter_name = r.recruiter_name.title()
                normalized_names += 1
                needs_update = True

            # Review Flags
            if r.phone in dup_phone_set:
                review_reasons.append("Shared Phone Number (Possible Duplicate)")
            if r.company_id and (r.recruiter_name, r.company_id) in dup_nc_set:
                review_reasons.append("Shared Name & Company (Possible Duplicate)")
            if "@missing.local" in (r.email or ""):
                review_reasons.append("Dummy Email / Phone-Only Contact")

            if review_reasons:
                r.needs_review = True
                r.review_reason = " | ".join(review_reasons)
                flagged_reviews += 1
                needs_update = True
            else:
                if r.needs_review:
                    r.needs_review = False
                    r.review_reason = None
                    needs_update = True

            # State Inference
            if not r.state and r.location:
                inferred, conf, reason = infer_state(r.location)
                if inferred:
                    r.state = inferred
                    r.state_source = 'recruiter_location'
                    r.state_confidence = conf
                    r.state_reason = reason
                    inferred_states += 1
                    needs_update = True

            # Tracking timestamp
            r.last_scan_at = scan_time
            needs_update = True

            # Completeness Score (0-100)
            score = 0
            if r.recruiter_name and r.recruiter_name != 'Unknown': score += 20
            if r.email and "@missing.local" not in r.email: score += 20
            if r.phone: score += 20
            if r.company_id: score += 20
            if r.state: score += 20
            
            if r.completeness_score != score:
                r.completeness_score = score
                needs_update = True

            if needs_update:
                updates += 1

        processed += len(recruiters)
        print(f"Processed {processed} / {total_recruiters} records...")
        
        if not dry_run:
            db.commit()

    print("\n--- RESULTS ---")
    print(f"Records touched/updated: {updates}")
    print(f"States safely inferred: {inferred_states}")
    print(f"Records flagged for manual review: {flagged_reviews}")
    print(f"Names normalized (casing): {normalized_names}")

    if not dry_run:
        print("\nAll batches committed to database.")
    else:
        print("\nRolling back dry-run session...")
        db.rollback()

    db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually run the updates against the database")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of records to process per commit")
    args = parser.parse_args()
    
    run_engine(dry_run=not args.execute, batch_size=args.batch_size)
