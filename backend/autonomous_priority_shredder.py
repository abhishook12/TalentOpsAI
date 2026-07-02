import os
import time
import logging
import pandas as pd
from sqlalchemy import text
from app.database import SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("priority_shredder")

ARCHIVE_DIR = "c:/TalentOpsAI/exports/archives"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def get_db_size_mb(db) -> float:
    try:
        bytes_sz = db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
        return round(bytes_sz / (1024 * 1024), 2)
    except Exception:
        return 0.0

def run_priority_shredder_cycle():
    logger.info("=========================================================")
    logger.info("AUTONOMOUS PRIORITY SHREDDER & NIGHT WORKER ENGAGED")
    logger.info("Mode: Continuous Quality Tier Enforcer & 500MB Deflator")
    logger.info("=========================================================")
    
    db = SessionLocal()
    start_mb = get_db_size_mb(db)
    logger.info(f"Initial Live Database Footprint: {start_mb} MB")
    
    # 1. Audit Tier Breakdown
    logger.info("Auditing current Profile Quality Tiers...")
    tier_sql = text("""
        SELECT 
            CASE 
                WHEN (email IS NOT NULL AND email != '') AND (phone IS NOT NULL AND phone != '') AND (state IS NOT NULL AND state != '') THEN 'Tier 1: Gold (Name+Email+Phone+State)'
                WHEN (email IS NOT NULL AND email != '') AND (phone IS NOT NULL AND phone != '') THEN 'Tier 2: Silver (Name+Email+Phone)'
                ELSE 'Tier 3/4: Bronze/Shred Target (Missing Email or Phone)'
            END as tier, count(*)
        FROM recruiters GROUP BY 1 ORDER BY 1
    """)
    tiers = db.execute(tier_sql).fetchall()
    for t_name, t_cnt in tiers:
        logger.info(f"  -> {t_name}: {t_cnt:,} profiles")
        
    # 2. Identify Low-Priority Profiles for Archiving (Missing Email OR Missing Phone)
    logger.info("Extracting Low-Priority incomplete profiles for disk archiving...")
    low_priority_sql = text("""
        SELECT recruiter_id, recruiter_name, title, email, phone, state 
        FROM recruiters 
        WHERE (email IS NULL OR email = '') OR (phone IS NULL OR phone = '')
        LIMIT 50000
    """)
    rows = db.execute(low_priority_sql).fetchall()
    
    if not rows:
        logger.info("VICTORY: Zero incomplete profiles found! Database is 100% Gold/Silver Quality.")
        db.close()
        return
        
    logger.info(f"Archiving batch of {len(rows):,} low-priority profiles to disk before shedding...")
    df = pd.DataFrame(rows, columns=["recruiter_id", "recruiter_name", "title", "email", "phone", "state"])
    archive_path = os.path.join(ARCHIVE_DIR, f"shredded_archive_{int(time.time())}.csv")
    df.to_csv(archive_path, index=False)
    logger.info(f"Safely backed up {len(rows):,} profiles to {archive_path} (Zero data loss!).")
    
    # 3. Shred from active PostgreSQL
    shred_ids = tuple(r[0] for r in rows)
    logger.info(f"Shredding {len(shred_ids):,} low-priority rows from active PostgreSQL table...")
    
    # Chunked deletion to avoid locking
    chunk_size = 5000
    for i in range(0, len(shred_ids), chunk_size):
        sub_ids = shred_ids[i:i+chunk_size]
        if len(sub_ids) == 1:
            db.execute(text(f"DELETE FROM recruiters WHERE recruiter_id = '{sub_ids[0]}'"))
        else:
            db.execute(text(f"DELETE FROM recruiters WHERE recruiter_id IN {sub_ids}"))
        db.commit()
        
    end_mb = get_db_size_mb(db)
    logger.info("=========================================================")
    logger.info("SHRED CYCLE COMPLETE")
    logger.info(f"Profiles Shredded & Archived: {len(rows):,}")
    logger.info(f"Database Footprint Evolution: {start_mb} MB -> {end_mb} MB")
    logger.info("=========================================================")
    db.close()

if __name__ == "__main__":
    while True:
        try:
            run_priority_shredder_cycle()
            logger.info("Resting 30 seconds before next continuous shred cycle...")
            time.sleep(30)
        except Exception as e:
            logger.error(f"Shredder error: {e}")
            time.sleep(15)
