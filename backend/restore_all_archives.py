import glob
import logging
import pandas as pd
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("restore_archives")

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def main():
    logger.info("Connecting to single unified database...")
    conn = psycopg.connect(DB_URL, prepare_threshold=None)
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM recruiters")
    start_count = cur.fetchone()[0]
    logger.info(f"Starting DB count: {start_count:,} recruiters.")

    archive_files = glob.glob("c:/TalentOpsAI/exports/archives/*.csv")
    logger.info(f"Found {len(archive_files)} archive files to restore into single database.")

    total_restored = 0
    for af in archive_files:
        logger.info(f"Processing archive: {af}")
        try:
            df = pd.read_csv(af, dtype=str, on_bad_lines='skip')
        except Exception as e:
            logger.error(f"Error reading {af}: {e}")
            continue

        records = []
        for _, row in df.iterrows():
            name = str(row.get('recruiter_name', '')).strip()
            if not name or name.lower() in ['nan', 'null', 'none']:
                continue
            email = str(row.get('email', '')).strip()
            phone = str(row.get('phone', '')).strip()
            title = str(row.get('title', 'Professional')).strip()
            if title.lower() in ['nan', 'null']: title = 'Professional'
            
            score = 60
            try:
                score = int(float(str(row.get('completeness_score', 60))))
            except:
                pass

            records.append((
                name[:100],
                email[:100] if email and email != 'nan' else None,
                phone[:30] if phone and phone != 'nan' else None,
                title[:100],
                score
            ))

        if records:
            logger.info(f"Injecting batch of {len(records):,} records from {af}...")
            for i in range(0, len(records), 2000):
                chunk = records[i:i+2000]
                cur.executemany("""
                    INSERT INTO recruiters (recruiter_name, email, phone, title, completeness_score)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, chunk)
            conn.commit()
            total_restored += len(records)
            logger.info(f"Restored so far: {total_restored:,}")

    cur.execute("SELECT count(*) FROM recruiters")
    final_count = cur.fetchone()[0]
    logger.info(f"=== RESTORE COMPLETE ===")
    logger.info(f"Final DB count: {final_count:,} recruiters unified in single platform.")
    conn.close()

if __name__ == "__main__":
    main()
