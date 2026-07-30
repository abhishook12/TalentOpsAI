import os
import sys
import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.models import Recruiter
from app.services.enrichment_service import jit_enrichment_service

load_dotenv()
remote_url = os.getenv("DATABASE_URL")
if not remote_url:
    remote_url = "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
elif remote_url.startswith("postgresql+psycopg://"):
    remote_url = remote_url.replace("postgresql+psycopg://", "postgresql://")

# Use a connection pool for multithreading, and disable prepared statements for PgBouncer
engine = create_engine(remote_url, pool_size=20, max_overflow=0, connect_args={"prepare_threshold": None})
Session = sessionmaker(bind=engine)

def process_recruiter(rec_id):
    session = Session()
    try:
        rec = session.query(Recruiter).filter(Recruiter.recruiter_id == rec_id).first()
        if not rec:
            return False
        
        # Random sleep to avoid instant DDG bans
        time.sleep(random.uniform(1.0, 5.0))
        
        enriched = jit_enrichment_service.enrich_recruiter_sync(session, rec)
        return enriched
    except Exception as e:
        print(f"Error processing {rec_id}: {e}")
        return False
    finally:
        session.close()

from app.utils.enricher_state import get_enricher_state, set_enricher_state

def run_enricher_loop():
    print("Starting massive scale background enrichment daemon...")
    set_enricher_state({"status": "running"})
    while True:
        # Check State
        state = get_enricher_state()
        if state["status"] == "stopped":
            print("Received STOP command. Exiting daemon gracefully.")
            break
        if state["status"] == "paused":
            print("Received PAUSE command. Pausing for 5 seconds...")
            time.sleep(5)
            continue
            
        session = Session()
        try:
            print("Fetching next batch of recruiters missing data...")
            # Fetch recruiters missing phone or location
            # Prioritize those with a company_id
            recruiters = session.query(Recruiter.recruiter_id).filter(
                Recruiter.company_id.isnot(None),
                (Recruiter.phone.is_(None)) | (Recruiter.location.is_(None))
            ).limit(200).all()
            
            if not recruiters:
                print("No more recruiters to enrich. Sleeping for 1 hour...")
                time.sleep(3600)
                continue
                
            rec_ids = [r[0] for r in recruiters]
            print(f"Found {len(rec_ids)} records. Submitting to thread pool...")
            
            success_count = 0
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(process_recruiter, r_id): r_id for r_id in rec_ids}
                for future in as_completed(futures):
                    if future.result():
                        success_count += 1
                        
            print(f"Batch complete. Successfully enriched {success_count} out of {len(rec_ids)}.")
            
            # Update state with metrics
            state = get_enricher_state()
            set_enricher_state({
                "records_processed": state.get("records_processed", 0) + len(rec_ids),
                "success_count": state.get("success_count", 0) + success_count
            })
            
        except Exception as e:
            print(f"Daemon Error: {e}")
            time.sleep(10)
        finally:
            session.close()

if __name__ == "__main__":
    run_enricher_loop()

