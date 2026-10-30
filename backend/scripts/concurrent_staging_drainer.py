"""
High-Throughput Concurrent Discovery Staging Drainer
Processes pending staging records concurrently using a thread pool.
Each thread uses its own dedicated SessionLocal database session.
"""
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.staging_models import DiscoveryStaging
from app.services.ingestion_funnel import universal_funnel

def process_single_record(staged_id: int) -> dict:
    db = SessionLocal()
    try:
        staged = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staged_id).first()
        if not staged or (staged.processed_at is not None and staged.processing_status not in ("pending", "batched")):
            return {"id": staged_id, "status": "SKIPPED"}
        
        res = universal_funnel.process_staging_record(staged, db)
        db.commit()
        return {"id": staged_id, "status": res.get("status", "OK"), "gate": res.get("gate")}
    except Exception as e:
        db.rollback()
        try:
            # Mark error so it doesn't loop
            err_staged = db.query(DiscoveryStaging).filter(DiscoveryStaging.id == staged_id).first()
            if err_staged:
                err_staged.processing_status = "held_review"
                err_staged.decision = "ERROR_UNHANDLED"
                err_staged.decision_reason = str(e)[:250]
                err_staged.processed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
        return {"id": staged_id, "status": "ERROR", "error": str(e)}
    finally:
        db.close()

def run_concurrent_drain(batch_chunk: int = 100, workers: int = 10):
    main_db = SessionLocal()
    try:
        total_pending = main_db.query(DiscoveryStaging).filter(
            (DiscoveryStaging.processing_status.in_(["pending", "batched"])) |
            (DiscoveryStaging.processed_at == None)
        ).count()
        print(f"[Concurrent Drainer] Total pending records: {total_pending} with {workers} parallel workers", flush=True)
    finally:
        main_db.close()

    total_done = 0
    t0 = time.time()

    while True:
        # Fetch chunk of IDs with retry resilience
        record_ids = []
        for fetch_attempt in range(5):
            fetch_db = SessionLocal()
            try:
                id_rows = fetch_db.query(DiscoveryStaging.id).filter(
                    (DiscoveryStaging.processing_status.in_(["pending", "batched"])) |
                    (DiscoveryStaging.processed_at == None)
                ).order_by(DiscoveryStaging.id.asc()).limit(batch_chunk).all()
                record_ids = [r[0] for r in id_rows]
                break
            except Exception as fe:
                print(f"[Concurrent Drainer] Fetch attempt {fetch_attempt+1} warning: {fe}. Retrying in 2s...", flush=True)
                time.sleep(2)
            finally:
                fetch_db.close()

        if not record_ids:
            print("[Concurrent Drainer] All pending records processed!", flush=True)
            break

        chunk_start = time.time()
        promoted = 0
        enriched = 0
        rejected = 0
        reviewed = 0
        errors = 0

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_id = {executor.submit(process_single_record, rid): rid for rid in record_ids}
                for future in as_completed(future_to_id):
                    try:
                        res = future.result()
                        status = res.get("status")
                        if status == "PROMOTED":
                            promoted += 1
                        elif status == "ENRICHED":
                            enriched += 1
                        elif status == "REJECTED":
                            rejected += 1
                        elif status == "HELD_REVIEW":
                            reviewed += 1
                        elif status == "ERROR":
                            errors += 1
                    except Exception as exc:
                        errors += 1
        except Exception as chunk_err:
            print(f"[Concurrent Drainer] Chunk executor warning: {chunk_err}", flush=True)

        total_done += len(record_ids)
        elapsed = time.time() - chunk_start
        print(
            f"[Chunk Done] Processed {len(record_ids)} in {elapsed:.1f}s | "
            f"Promoted: {promoted} | Enriched: {enriched} | Rejected: {rejected} | Held: {reviewed} | Errors: {errors} | "
            f"Total Completed: {total_done}/{total_pending}",
            flush=True
        )

    total_time = time.time() - t0
    print(f"[Concurrent Drainer] Finished draining {total_done} records in {total_time:.1f}s ({total_time/60:.2f} mins)!", flush=True)

if __name__ == '__main__':
    run_concurrent_drain()
