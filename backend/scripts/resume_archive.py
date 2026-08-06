import os, uuid, psycopg, time
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')

DB_URL = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

def archive_remaining():
    print("=== RESUMING ARCHIVE: Moving remaining unknown recruiters to bucket ===", flush=True)
    conn = psycopg.connect(DB_URL, autocommit=True, prepare_threshold=None)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM recruiters WHERE email_status = 'unknown'")
    remaining = cur.fetchone()[0]
    print(f"Remaining unknown recruiters to archive: {remaining:,}", flush=True)
    
    if remaining == 0:
        print("Nothing to archive!")
        return
    
    # Delete in small safe batches to avoid locks/timeouts
    batch_size = 5000
    total_deleted = 0
    start = time.time()
    
    while True:
        cur.execute("""
            SELECT recruiter_id FROM recruiters 
            WHERE email_status = 'unknown' 
            LIMIT %s
        """, (batch_size,))
        ids = [r[0] for r in cur.fetchall()]
        
        if not ids:
            break
        
        # Delete related records first
        cur.execute("DELETE FROM mailintel_evidence WHERE email_id IN (SELECT id FROM recruiter_emails WHERE recruiter_id = ANY(%s))", (ids,))
        cur.execute("DELETE FROM mailintel_tracking WHERE email_id IN (SELECT id FROM recruiter_emails WHERE recruiter_id = ANY(%s))", (ids,))
        cur.execute("DELETE FROM recruiter_emails WHERE recruiter_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM campaign_recruiters WHERE recruiter_id = ANY(%s)", (ids,))
        cur.execute("DELETE FROM recruiters WHERE recruiter_id = ANY(%s)", (ids,))
        
        total_deleted += len(ids)
        elapsed = time.time() - start
        rate = total_deleted / elapsed if elapsed > 0 else 0
        print(f"  Deleted {total_deleted:,} / {remaining:,} ({total_deleted*100//remaining}%) | {rate:.0f} rows/sec", flush=True)
    
    # Check final size
    cur.execute("SELECT pg_database_size(current_database()) / 1048576.0")
    size = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM recruiters")
    total = cur.fetchone()[0]
    
    elapsed = time.time() - start
    print(f"\n=== ARCHIVE COMPLETE ===")
    print(f"Deleted {total_deleted:,} unknown recruiters in {elapsed:.1f}s")
    print(f"Remaining recruiters: {total:,}")
    print(f"DB Size (before VACUUM): {size:.2f} MB")
    
    conn.close()

if __name__ == "__main__":
    archive_remaining()
