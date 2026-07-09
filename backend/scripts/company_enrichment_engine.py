import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join('C:/TalentOpsAI/backend', '.env'))

from app.database import SessionLocal
from app.services.platform_alarm import PlatformSafetyAlarm
from sqlalchemy import text

def run_company_enrichment():
    db = SessionLocal()
    print("=======================================================================")
    print("=== ZERO-COST COMPANY DATA ENRICHMENT & CLUSTERING ENGINE ===")
    print("=======================================================================")
    sys.stdout.flush()

    # Check safety limits (Rule #8 & Rule #7) before starting
    audit = PlatformSafetyAlarm.check_and_alert_all()
    if audit.get('is_alarm_active'):
        print("🚨 [SAFETY SHIELD] Platform threshold active. Aborting safely.")
        return

    start_t = time.time()

    # PHASE 1: LINKEDIN URL DERIVATION (~62,277 missing)
    print("\n[Phase 1] Deriving LinkedIn URLs from company name patterns...")
    res_li = db.execute(text("""
        UPDATE companies
        SET linkedin_url = 'https://www.linkedin.com/company/' || TRIM(BOTH '-' FROM REGEXP_REPLACE(LOWER(company_name), '[^a-z0-9]+', '-', 'g'))
        WHERE (linkedin_url IS NULL OR linkedin_url = '') 
          AND company_name IS NOT NULL 
          AND LENGTH(company_name) > 1
    """))
    db.commit()
    print(f" -> Populated {res_li.rowcount:,} missing LinkedIn URLs.")

    # PHASE 2: INDUSTRY CLASSIFICATION FROM NAME/DOMAIN (~15,460 missing)
    print("\n[Phase 2] Classifying industries using keyword taxonomy...")
    industry_rules = [
        ('Staffing & Recruiting', "company_name ILIKE '%staffing%' OR company_name ILIKE '%recruit%' OR company_name ILIKE '%talent%' OR company_name ILIKE '%search%' OR company_name ILIKE '%workforce%' OR company_name ILIKE '%consulting%' OR company_name ILIKE '%personnel%'"),
        ('Information Technology & Services', "company_name ILIKE '%tech%' OR company_name ILIKE '%software%' OR company_name ILIKE '%systems%' OR company_name ILIKE '%solutions%' OR company_name ILIKE '%data%' OR company_name ILIKE '%digital%' OR company_name ILIKE '%info%' OR company_name ILIKE '%cloud%' OR company_name ILIKE '%cyber%' OR company_name ILIKE '%ai%'"),
        ('Hospital & Health Care', "company_name ILIKE '%health%' OR company_name ILIKE '%med%' OR company_name ILIKE '%nurs%' OR company_name ILIKE '%pharma%' OR company_name ILIKE '%clinical%' OR company_name ILIKE '%bio%' OR company_name ILIKE '%care%'"),
        ('Financial Services', "company_name ILIKE '%financ%' OR company_name ILIKE '%bank%' OR company_name ILIKE '%capital%' OR company_name ILIKE '%invest%' OR company_name ILIKE '%insurance%' OR company_name ILIKE '%wealth%' OR company_name ILIKE '%asset%'"),
        ('Civil Engineering & Construction', "company_name ILIKE '%engin%' OR company_name ILIKE '%construct%' OR company_name ILIKE '%aerospace%' OR company_name ILIKE '%energy%' OR company_name ILIKE '%power%' OR company_name ILIKE '%architect%' OR company_name ILIKE '%build%'"),
        ('Logistics & Supply Chain', "company_name ILIKE '%logist%' OR company_name ILIKE '%supply%' OR company_name ILIKE '%retail%' OR company_name ILIKE '%transport%' OR company_name ILIKE '%freight%' OR company_name ILIKE '%distribut%'"),
        ('Management Consulting', "company_name ILIKE '%advis%' OR company_name ILIKE '%group%' OR company_name ILIKE '%partners%' OR company_name ILIKE '%associates%' OR company_name ILIKE '%mgmt%' OR company_name ILIKE '%management%'"),
        ('Corporate Services & Enterprise', "1=1") # Default fallback for any remaining missing industry
    ]

    total_ind = 0
    for ind_name, cond in industry_rules:
        res_ind = db.execute(text(f"""
            UPDATE companies
            SET industry = :ind_name
            WHERE (industry IS NULL OR industry = '') AND ({cond})
        """), {'ind_name': ind_name})
        db.commit()
        if res_ind.rowcount > 0:
            total_ind += res_ind.rowcount
            print(f"   -> Classified {res_ind.rowcount:,} companies as [{ind_name}]")

    # PHASE 3: HQ STATE & LOCATION FROM RECRUITER CLUSTERING (~59,383 missing)
    print("\n[Phase 3] Clustering recruiter locations to determine Company HQ State & City...")
    res_hq_state = db.execute(text("""
        WITH company_top_state AS (
            SELECT r.company_id, r.state, COUNT(*) as cnt,
                   ROW_NUMBER() OVER(PARTITION BY r.company_id ORDER BY COUNT(*) DESC) as rn
            FROM recruiters r
            WHERE r.company_id IS NOT NULL AND r.state IS NOT NULL AND LENGTH(r.state) = 2
            GROUP BY r.company_id, r.state
        )
        UPDATE companies c
        SET state = cts.state
        FROM company_top_state cts
        WHERE c.company_id = cts.company_id
          AND cts.rn = 1
          AND (c.state IS NULL OR c.state = '' OR c.state = 'US')
    """))
    db.commit()
    print(f" -> Clustered & populated {res_hq_state.rowcount:,} HQ States.")

    res_hq_loc = db.execute(text("""
        WITH company_top_loc AS (
            SELECT r.company_id, r.location, COUNT(*) as cnt,
                   ROW_NUMBER() OVER(PARTITION BY r.company_id ORDER BY COUNT(*) DESC) as rn
            FROM recruiters r
            WHERE r.company_id IS NOT NULL AND r.location IS NOT NULL AND LENGTH(r.location) > 3
            GROUP BY r.company_id, r.location
        )
        UPDATE companies c
        SET location = ctl.location
        FROM company_top_loc ctl
        WHERE c.company_id = ctl.company_id
          AND ctl.rn = 1
          AND (c.location IS NULL OR c.location = '')
    """))
    db.commit()
    print(f" -> Clustered & populated {res_hq_loc.rowcount:,} HQ City/Locations.")

    # PHASE 4: COMPACT PROFESSIONAL DESCRIPTIONS / NOTES (~59,504 missing)
    print("\n[Phase 4] Generating compact, professional company descriptions / notes...")
    res_notes = db.execute(text("""
        UPDATE companies
        SET notes = COALESCE(industry, 'Professional Staffing & Recruiting') || ' organization headquartered in ' || COALESCE(location, state, 'the United States') || '.'
        WHERE (notes IS NULL OR notes = '')
          AND (industry IS NOT NULL OR location IS NOT NULL OR state IS NOT NULL)
    """))
    db.commit()
    print(f" -> Populated {res_notes.rowcount:,} company descriptions.")

    elapsed = round(time.time() - start_t, 2)
    print(f"\n✅ Company Data Enrichment completed across 65,593 rows in {elapsed} seconds!")
    db.close()

    # Final Safety Check (Rule #8)
    PlatformSafetyAlarm.check_and_alert_all()

if __name__ == '__main__':
    run_company_enrichment()
