import sys, os, json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.models.models import Recruiter

def run_db_verification():
    print("=" * 60)
    print("CHECK 2: DATABASE STAGING & PROMOTION INTEGRITY (TEAMS HARVEST)")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Total Staged Teams Records
        cnt_staging = db.query(DiscoveryStaging).filter(
            (DiscoveryStaging.device_id.like("%TEAMS%")) |
            (DiscoveryStaging.batch_id.like("%TEAMS%"))
        ).count()
        print(f"\n[2.1] Total Teams Candidates in discovery_staging: {cnt_staging:,}")

        # 2. Total in the 20-minute Upward Stream Batch
        cnt_20min = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM"
        ).count()
        print(f"[2.2] Candidates in 20-Minute Run (batch_id='TEAMS_CTV_UPWARD_STREAM'): {cnt_20min}")

        # 3. Last Person Collected in the 20-minute run (Scott Tupper)
        last_rec = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM"
        ).order_by(DiscoveryStaging.id.desc()).first()
        print("\n[2.3] Last Person Collected at End of 20-Min Run:")
        if last_rec:
            meta = json.loads(last_rec.metadata_json or '{}')
            print(f"  - Name: {last_rec.raw_name}")
            print(f"  - Company: {last_rec.raw_company}")
            print(f"  - Primary Email: {last_rec.raw_email}")
            print(f"  - Secondary Email: {meta.get('email2')}")
            print(f"  - Primary Phone: {last_rec.raw_phone}")
            print(f"  - Secondary Phones: {meta.get('all_phones')}")
            print(f"  - Decision / Status: {last_rec.decision}")
        else:
            print("  - WARNING: No candidate found in batch_id='TEAMS_CTV_UPWARD_STREAM'")

        # 4. Multi-Contact Field Separation Check
        multi_records = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.batch_id == "TEAMS_CTV_UPWARD_STREAM"
        ).all()
        multi_phone_count = 0
        multi_email_count = 0
        four_phone_samples = []

        for r in multi_records:
            m = json.loads(r.metadata_json or '{}')
            phones = m.get("all_phones", [])
            emails = m.get("all_emails", [])
            if len(phones) >= 2 or m.get("phone2"):
                multi_phone_count += 1
            if len(emails) >= 2 or m.get("email2"):
                multi_email_count += 1
            if m.get("phone4"):
                four_phone_samples.append({
                    "name": r.raw_name,
                    "company": r.raw_company,
                    "p1": r.raw_phone,
                    "p2": m.get("phone2"),
                    "p3": m.get("phone3"),
                    "p4": m.get("phone4")
                })

        print(f"\n[2.4] Verified Multi-Contact Separation:")
        print(f"  - Candidates with 2+ Phones: {multi_phone_count}")
        print(f"  - Candidates with 2+ Emails: {multi_email_count}")
        print(f"  - Candidates with 4 Distinct Separated Phones: {len(four_phone_samples)}")
        for s in four_phone_samples:
            print(f"    * {s['name']} ({s['company']}): P1={s['p1']} | P2={s['p2']} | P3={s['p3']} | P4={s['p4']}")

        # 5. Master Postgres Recruiters Count for Teams
        teams_master = db.query(Recruiter).filter(
            Recruiter.data_source.ilike("%teams%")
        ).count()
        print(f"\n[2.5] Total Teams Candidates in Master PostgreSQL 'recruiters' Table: {teams_master:,}")

        # 6. Overall Catalog Total
        cat_total = db.query(Recruiter).count()
        print(f"[2.6] Overall Master Recruiter Catalog Size: {cat_total:,}")

    finally:
        db.close()

if __name__ == "__main__":
    run_db_verification()
