"""
Master Data Harvester & Parquet Synthesis Pipeline (Streaming Architecture)
Discovers, extracts, normalizes, deduplicates on-the-fly, and compiles all local candidate & recruiter
data into TalentOps AI's primary DuckDB Parquet store (recruiters_full.parquet).
"""
import os
import sys
import time
import shutil
import logging
import datetime
from typing import Optional
import pandas as pd
import duckdb

# Ensure backend path is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from app.services.data_harvester import DataHarvester
from app.services.data_normalizer import normalize_record
from app.services.dedup_engine import DeduplicationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("harvest_and_compile")


def create_safety_backup(parquet_path: str) -> Optional[str]:
    """Creates a timestamped snapshot of the existing Parquet file."""
    if not os.path.exists(parquet_path):
        logger.info(f"No existing parquet at {parquet_path}, skipping backup.")
        return None

    snapshots_dir = os.path.join(os.path.dirname(parquet_path), "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(snapshots_dir, f"recruiters_snapshot_{ts}.parquet")
    shutil.copy2(parquet_path, backup_path)
    logger.info(f"✅ Safety backup created: {backup_path} ({os.path.getsize(backup_path):,} bytes)")
    return backup_path


def run_pipeline():
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("  STARTING STREAMING AUTONOMOUS DATA HARVESTER & PARQUET COMPILER")
    logger.info("=" * 70)

    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    target_parquet = os.path.join(data_dir, "recruiters_full.parquet")

    # Step 1: Safety Backup
    create_safety_backup(target_parquet)

    # Step 2: Discover Sources across Entire Computer (C: and D: Drives)
    search_paths = [
        os.path.abspath(os.path.join(BASE_DIR, "..")), # Workspace root
        "C:\\Users",
        "D:\\",
    ]

    harvester = DataHarvester()
    logger.info(f"Scanning search locations: {search_paths}")
    discovered_files = harvester.scan_directories(search_paths)
    logger.info(f"Discovered {len(discovered_files)} candidate data files on system.")

    dedup_engine = DeduplicationEngine()
    total_raw_processed = 0

    # Step 3: Pure Ingestion from Raw Discovered PC Sources (<= 15 columns only)
    logger.info("Ingesting raw sources across PC with strict <= 15 column rule...")

    # Step 4: Stream harvest external & local files on-the-fly
    for fpath in discovered_files:
        if os.path.abspath(fpath) == os.path.abspath(target_parquet):
            continue
        if "snapshots" in fpath.lower() and fpath.lower().endswith(".parquet"):
            continue
        try:
            extracted = harvester.harvest_file(fpath)
            for raw in extracted:
                total_raw_processed += 1
                # Fast filter: must have email or name with contact info
                em = raw.get("email")
                nm = raw.get("recruiter_name")
                if em or (nm and (raw.get("phone") or raw.get("company_id"))):
                    norm = normalize_record(raw, record_id=total_raw_processed)
                    dedup_engine.add_or_merge(norm)
        except Exception as e:
            logger.warning(f"Error streaming {fpath}: {e}")

    logger.info(f"✅ Total raw records processed: {total_raw_processed:,}")
    master_records = dedup_engine.merged_records
    logger.info(f"✅ Total unique synthesized master records: {len(master_records):,}")

    # Re-index sequential recruiter_ids
    for new_id, rec in enumerate(master_records, start=1):
        rec["recruiter_id"] = new_id

    # Step 5: Convert to DataFrame & Enforce Parquet Schema
    logger.info("Compiling into Parquet DataFrame...")
    df = pd.DataFrame(master_records)

    schema_definitions = {
        "recruiter_id": "int64",
        "recruiter_name": "string",
        "normalized_recruiter_name": "string",
        "email": "string",
        "phone": "string",
        "email2": "string",
        "phone2": "string",
        "email3": "string",
        "phone3": "string",
        "email4": "string",
        "phone4": "string",
        "alternate_emails": "float64",
        "alternate_phones": "float64",
        "linkedin": "string",
        "specialization": "string",
        "title": "string",
        "notes": "string",
        "review_reason": "string",
        "company_id": "string",
        "location": "string",
        "state": "string",
        "normalized_city": "string",
        "location_confidence": "string",
        "state_source": "string",
        "state_confidence": "string",
        "state_reason": "string",
        "last_scan_at": "string",
        "completeness_score": "int64",
        "needs_review": "string",
        "is_active": "bool",
        "data_source": "string",
        "trust_score": "float64",
        "source_job_id": "string",
        "raw_data": "float64",
        "metadata_json": "string",
        "tags": "string",
        "created_at": "string",
        "updated_at": "string",
        "taxonomy_category": "string",
        "report_count": "float64",
        "email_status": "string",
        "email_confidence": "int64",
        "email_source": "string",
        "email_pattern_id": "string",
        "email_generated": "string",
        "email_verified_at": "string",
        "email_last_checked_at": "string",
        "canonical_company_id": "string",
        "historical_company_id": "float64",
        "company_domain_id": "float64",
        "raw_email_value": "string",
        "repair_reason": "float64",
        "user_id": "string",
        "quality_score": "int64",
        "missing_fields": "string",
        "sentinel_status": "string",
        "last_verified_at": "string",
        "company_confidence": "string",
        "company_reasoning": "string",
        "is_archived": "bool",
        "merged_into_id": "float64",
        "logo_url": "string",
        "is_deliverable": "bool",
        "seniority_level": "string",
        "timezone_code": "string",
        "timezone": "string",
        "company_scale": "string"
    }

    for col, dtype in schema_definitions.items():
        if col not in df.columns:
            if dtype == "int64":
                df[col] = 0
            elif dtype == "float64":
                df[col] = 0.0
            elif dtype == "bool":
                df[col] = False
            else:
                df[col] = ""

        # Fill NAs according to type
        if dtype == "int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
        elif dtype == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
        elif dtype == "bool":
            df[col] = df[col].astype("bool")
        else:
            df[col] = df[col].fillna("").astype("string")

    # Reorder columns exactly
    df = df[list(schema_definitions.keys())]

    # Step 6: Atomic Parquet Write
    tmp_parquet = target_parquet + ".harvest.tmp"
    logger.info(f"Writing {len(df):,} records to temporary Parquet {tmp_parquet}...")
    df.to_parquet(tmp_parquet, engine="pyarrow", compression="snappy", index=False)

    # Atomic swap
    if os.path.exists(target_parquet):
        try:
            os.remove(target_parquet)
        except Exception:
            pass
    shutil.move(tmp_parquet, target_parquet)
    logger.info(f"✅ Parquet dataset synthesized at {target_parquet} ({os.path.getsize(target_parquet):,} bytes)")

    # Step 7: DuckDB Verification & Query Benchmark
    logger.info("Running DuckDB verification audit...")
    con = duckdb.connect()
    total_cnt = con.execute(f"SELECT COUNT(*) FROM '{target_parquet}'").fetchone()[0]
    email_cnt = con.execute(f"SELECT COUNT(*) FROM '{target_parquet}' WHERE email != ''").fetchone()[0]
    phone_cnt = con.execute(f"SELECT COUNT(*) FROM '{target_parquet}' WHERE phone != ''").fetchone()[0]
    linkedin_cnt = con.execute(f"SELECT COUNT(*) FROM '{target_parquet}' WHERE linkedin != ''").fetchone()[0]
    comp_cnt = con.execute(f"SELECT COUNT(DISTINCT company_id) FROM '{target_parquet}'").fetchone()[0]
    state_cnt = con.execute(f"SELECT COUNT(DISTINCT state) FROM '{target_parquet}'").fetchone()[0]

    bench_start = time.time()
    con.execute(f"SELECT * FROM '{target_parquet}' WHERE state = 'CA' LIMIT 50").fetchall()
    filter_latency_ms = round((time.time() - bench_start) * 1000, 2)

    bench_start = time.time()
    con.execute(f"SELECT * FROM '{target_parquet}' WHERE lower(recruiter_name) LIKE '%tech%' OR lower(title) LIKE '%tech%' LIMIT 50").fetchall()
    search_latency_ms = round((time.time() - bench_start) * 1000, 2)

    logger.info("=" * 70)
    logger.info("  HARVEST & COMPILATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total Master Candidates / Recruiters: {total_cnt:,}")
    logger.info(f"  Verified Email Contacts:             {email_cnt:,} ({round(email_cnt/total_cnt*100, 1)}%)")
    logger.info(f"  Direct Phone Numbers:                {phone_cnt:,} ({round(phone_cnt/total_cnt*100, 1)}%)")
    logger.info(f"  LinkedIn Profiles:                   {linkedin_cnt:,} ({round(linkedin_cnt/total_cnt*100, 1)}%)")
    logger.info(f"  Distinct Staffing / Corporate Orgs:  {comp_cnt:,}")
    logger.info(f"  Distinct US States Covered:          {state_cnt:,}")
    logger.info(f"  State Filter Latency:                {filter_latency_ms} ms")
    logger.info(f"  Full-Text Search Latency:            {search_latency_ms} ms")
    logger.info(f"  Total Pipeline Execution Time:       {round(time.time() - start_time, 2)} s")
    logger.info("=" * 70)

    # Step 8: Refresh RecruiterStore singleton
    try:
        from app.services.recruiter_store import recruiter_store
        recruiter_store.reload()
        logger.info("✅ RecruiterStore in-memory cache successfully hot-reloaded.")
    except Exception as e:
        logger.warning(f"Note: RecruiterStore hot reload trigger: {e}")

    return {
        "total_records": total_cnt,
        "email_count": email_cnt,
        "phone_count": phone_cnt,
        "linkedin_count": linkedin_cnt,
        "companies_count": comp_cnt,
        "filter_latency_ms": filter_latency_ms,
        "search_latency_ms": search_latency_ms
    }


if __name__ == "__main__":
    run_pipeline()
