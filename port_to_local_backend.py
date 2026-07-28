import sqlite3
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SOURCE_DB = r"C:\TalentOpsAI\local_deep_extract.db"
TARGET_DB = r"C:\TalentOpsAI\backend\dev.db"

def setup_indexes(cursor):
    logging.info("Creating local UI performance indexes...")
    # Index for fast search and duplicate prevention on dev.db
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_recruiters_email ON recruiters(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_recruiters_name ON recruiters(recruiter_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_recruiters_source ON recruiters(data_source)")

def run_local_port():
    logging.info("Connecting to Local Source DB...")
    src_conn = sqlite3.connect(SOURCE_DB)
    src_cursor = src_conn.cursor()
    
    logging.info("Connecting to Local Backend DB (dev.db)...")
    tgt_conn = sqlite3.connect(TARGET_DB)
    tgt_cursor = tgt_conn.cursor()
    
    setup_indexes(tgt_cursor)
    tgt_conn.commit()

    logging.info("Fetching existing local backend emails to ensure clean deduplication...")
    tgt_cursor.execute("SELECT email FROM recruiters WHERE email IS NOT NULL")
    existing_emails = {row[0].strip().lower() for row in tgt_cursor.fetchall()}
    logging.info(f"Local backend currently has {len(existing_emails)} unique emails.")
    
    logging.info("Streaming highly-compressed records from source DB...")
    src_cursor.execute("SELECT email, name FROM recruiters")
    
    batch_size = 10000
    insert_batch = []
    total_inserted = 0
    start_time = time.time()
    
    while True:
        rows = src_cursor.fetchmany(batch_size)
        if not rows:
            break
            
        for row in rows:
            email = row[0]
            name = row[1] if row[1] else "Unknown"
            
            clean_email = email.strip().lower()
            if clean_email not in existing_emails:
                existing_emails.add(clean_email)
                insert_batch.append((
                    name, 
                    clean_email, 
                    'system_deep_extract',
                    1, # is_active
                    0, # needs_review
                    100 # trust_score
                ))
                
        if len(insert_batch) >= batch_size:
            tgt_cursor.executemany("""
                INSERT OR IGNORE INTO recruiters 
                (recruiter_name, email, data_source, is_active, needs_review, trust_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insert_batch)
            tgt_conn.commit()
            total_inserted += len(insert_batch)
            logging.info(f"Inserted {total_inserted} local records...")
            insert_batch.clear()

    if insert_batch:
        tgt_cursor.executemany("""
            INSERT OR IGNORE INTO recruiters 
            (recruiter_name, email, data_source, is_active, needs_review, trust_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, insert_batch)
        tgt_conn.commit()
        total_inserted += len(insert_batch)

    logging.info(f"--- LOCAL PORTING COMPLETE ---")
    logging.info(f"Successfully ported {total_inserted} new records directly into dev.db.")
    logging.info(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    tgt_cursor.execute("SELECT COUNT(*) FROM recruiters")
    final_count = tgt_cursor.fetchone()[0]
    logging.info(f"Total Local App UI Records Available: {final_count}")
    
    src_conn.close()
    tgt_conn.close()

if __name__ == "__main__":
    run_local_port()
