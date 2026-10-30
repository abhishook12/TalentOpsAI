"""
site_db_sync.py — Direct Site Database Bridge for Teams Extractor.

Enables the Teams Extractor (both Vision and UIA engines) to send extracted
contacts directly to the main TalentOps AI PostgreSQL database (discovery_staging table)
instead of just saving to local Excel files.

Features:
- High-Performance Bulk Ingestion: Batched WAN queries & commits for lightning-fast sync.
- Strict Idempotency: Deterministic collision-proof discovery_id hash prevents duplicates.
- Gate Rule 5 Compliant: Automatically filters out synthetic placeholder emails.
- Historical Migration: Ingests all past Excel spreadsheets from teams_extractor/output/*.xlsx.
"""

import os
import sys
import glob
import re
import json
import hashlib
import time
import logging
from typing import List, Dict, Any, Tuple, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [SiteDBSync] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("talentops.site_db_sync")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com',
    'gateway.net', 'sbcglobal.net', 'att.net', 'verizon.net'
}

def clean_phone(raw: Optional[str]) -> Optional[str]:
    """Cleans phone numbers into normalized format."""
    if not raw:
        return None
    first_phone = re.split(r'[;,|]', str(raw))[0].strip()
    digits = re.sub(r'\D', '', first_phone)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) >= 10:
        return f"+{digits}" if not first_phone.startswith('+') else f"+{digits}"
    return first_phone if len(first_phone) >= 7 else None


def clean_email(raw: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Extracts valid primary email and list of all emails."""
    if not raw:
        return None, []
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(raw))
    if not emails:
        return None, []
    
    unique_emails = list(dict.fromkeys(emails))
    # Filter out synthetic placeholders per Gate Rule 5
    valid_emails = [e for e in unique_emails if not any(b in e.lower() for b in ['@unknown.com', '@noemail.talentops'])]
    if not valid_emails:
        return None, []
    
    corp_emails = [e for e in valid_emails if e.split('@')[-1].lower() not in FREE_EMAIL_DOMAINS]
    primary = corp_emails[0] if corp_emails else valid_emails[0]
    return primary, valid_emails


def generate_discovery_id(name: str, email: Optional[str], phone: Optional[str], fallback_idx: int = 0) -> str:
    """Generates a deterministic collision-proof discovery_id for idempotency."""
    seed = f"{name or ''}|{email or ''}|{phone or ''}".strip().lower()
    if seed == "||":
        seed = f"contact_{fallback_idx}_{time.time()}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()
    return f"TEAMS-EXT-{h}"


def sync_contacts_to_site_db(
    contacts: List[Dict[str, Any]],
    batch_id: str = "TEAMS_EXTRACTED_FEED",
    source_label: str = "teams_vision_extractor",
    owner_user_id: int = 1
) -> Tuple[int, int, int]:
    """
    Ingests in-memory contacts extracted by the extractor directly into Supabase PostgreSQL.
    Uses bulk queries and bulk insertion for maximum performance.
    """
    if not contacts:
        return (0, 0, 0)

    # 1. Parse and prepare all candidate records in memory
    prepared = []
    for idx, c in enumerate(contacts):
        name = (c.get("name") or "").strip()
        title = (c.get("title") or "").strip() or None
        company = (c.get("company") or "").strip() or None
        location = (c.get("location") or "").strip() or None
        linkedin = (c.get("linkedin") or "").strip() or None
        notes = (c.get("notes") or "").strip() or None

        raw_emails_list = []
        raw_phones_list = []

        for item in c.get("contacts", []):
            ctype = str(item.get("type", "")).lower()
            val = str(item.get("value", "")).strip()
            if not val:
                continue
            if "email" in ctype:
                raw_emails_list.append(val)
            elif "phone" in ctype:
                raw_phones_list.append(val)

        if c.get("emails"):
            raw_emails_list.extend(re.split(r'[;,]', str(c.get("emails"))))
        if c.get("phones"):
            raw_phones_list.extend(re.split(r'[;,]', str(c.get("phones"))))

        primary_email, all_emails = clean_email("; ".join(raw_emails_list))
        primary_phone = clean_phone("; ".join(raw_phones_list))

        if not name and not primary_email and not primary_phone:
            continue

        disc_id = generate_discovery_id(name, primary_email, primary_phone, idx)
        prepared.append({
            "disc_id": disc_id,
            "name": name,
            "title": title,
            "company": company,
            "location": location,
            "linkedin": linkedin,
            "primary_email": primary_email,
            "primary_phone": primary_phone,
            "all_emails": all_emails,
            "all_phones": raw_phones_list,
            "notes": notes
        })

    if not prepared:
        return (0, len(contacts), 0)

    db = SessionLocal()
    inserted = 0
    skipped = 0
    errors = 0

    try:
        # 2. Bulk check existing discovery_ids in chunks of 500
        all_disc_ids = [p["disc_id"] for p in prepared]
        existing_ids = set()
        chunk_size = 500
        for i in range(0, len(all_disc_ids), chunk_size):
            chunk = all_disc_ids[i:i + chunk_size]
            rows = db.query(DiscoveryStaging.discovery_id).filter(DiscoveryStaging.discovery_id.in_(chunk)).all()
            existing_ids.update(r[0] for r in rows)

        # 3. Create records for non-existing entries
        new_records = []
        seen_in_batch = set()
        for p in prepared:
            did = p["disc_id"]
            if did in existing_ids or did in seen_in_batch:
                skipped += 1
                continue
            seen_in_batch.add(did)

            metadata = {
                "all_emails": p["all_emails"],
                "all_phones": p["all_phones"],
                "notes": p["notes"],
                "original_source": source_label,
                "ingestion_method": "direct_site_db_sync"
            }

            rec = DiscoveryStaging(
                batch_id=batch_id[:64],
                discovery_id=did[:64],
                session_id=f"teams_sync_{int(time.time())}",
                device_id="TEAMS_EXTRACTOR_NODE",
                owner_user_id=owner_user_id,
                raw_name=p["name"][:200] if p["name"] else None,
                raw_title=p["title"][:200] if p["title"] else None,
                raw_company=p["company"][:255] if p["company"] else None,
                raw_email=p["primary_email"][:200] if p["primary_email"] else None,
                raw_phone=p["primary_phone"][:50] if p["primary_phone"] else None,
                raw_linkedin=p["linkedin"][:300] if p["linkedin"] else None,
                raw_location=p["location"][:255] if p["location"] else None,
                source_url="msteams:/l/chat/CTV-Phone-numbers",
                source_page_title="Microsoft Teams Extractor Feed",
                extraction_source="teams_extractor",
                processing_status="pending",
                metadata_json=json.dumps(metadata, ensure_ascii=False)
            )
            new_records.append(rec)

        # 4. Bulk insert in commits of 100
        commit_batch = 100
        for i in range(0, len(new_records), commit_batch):
            batch = new_records[i:i + commit_batch]
            db.add_all(batch)
            db.commit()
            inserted += len(batch)

    except Exception as e:
        logger.error(f"Error in bulk site DB ingestion: {e}")
        db.rollback()
        errors += 1
    finally:
        db.close()

    logger.info(f"Direct Site DB Sync Complete: {inserted} inserted, {skipped} skipped, {errors} errors.")
    return (inserted, skipped, errors)


def sync_excel_folder_to_site_db(output_dir: Optional[str] = None, owner_user_id: int = 1) -> Dict[str, Any]:
    """
    Scans the Excel output folder (teams_extractor/output/*.xlsx) and migrates
    all historical extracted contacts directly into the Supabase PostgreSQL discovery_staging table.
    """
    import openpyxl

    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), "output")

    excel_files = glob.glob(os.path.join(output_dir, "*.xlsx"))
    valid_files = [f for f in excel_files if not os.path.basename(f).startswith("~$")]
    logger.info(f"Discovered {len(valid_files)} valid Excel files in {output_dir}")

    total_rows = 0
    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    for file_path in valid_files:
        filename = os.path.basename(file_path)

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows or len(rows) <= 1:
                continue

            header = [str(h).strip().lower() if h else "" for h in rows[0]]
            col_map = {}
            for i, h in enumerate(header):
                if "name" in h: col_map["name"] = i
                elif "title" in h: col_map["title"] = i
                elif "company" in h: col_map["company"] = i
                elif "location" in h: col_map["location"] = i
                elif "email" in h: col_map["email"] = i
                elif "phone" in h: col_map["phone"] = i
                elif "linkedin" in h: col_map["linkedin"] = i
                elif "notes" in h: col_map["notes"] = i

            contacts_to_sync = []
            for r in rows[1:]:
                total_rows += 1
                name = str(r[col_map["name"]]).strip() if "name" in col_map and r[col_map["name"]] else ""
                title = str(r[col_map["title"]]).strip() if "title" in col_map and r[col_map["title"]] else ""
                company = str(r[col_map["company"]]).strip() if "company" in col_map and r[col_map["company"]] else ""
                location = str(r[col_map["location"]]).strip() if "location" in col_map and r[col_map["location"]] else ""
                email_val = str(r[col_map["email"]]).strip() if "email" in col_map and r[col_map["email"]] else ""
                phone_val = str(r[col_map["phone"]]).strip() if "phone" in col_map and r[col_map["phone"]] else ""
                linkedin = str(r[col_map["linkedin"]]).strip() if "linkedin" in col_map and r[col_map["linkedin"]] else ""
                notes = str(r[col_map["notes"]]).strip() if "notes" in col_map and r[col_map["notes"]] else ""

                contacts_to_sync.append({
                    "name": name,
                    "title": title,
                    "company": company,
                    "location": location,
                    "emails": email_val,
                    "phones": phone_val,
                    "linkedin": linkedin,
                    "notes": notes
                })

            batch_id = f"TEAMS_EXCEL_{re.sub(r'[^A-Za-z0-9_]', '_', filename.replace('.xlsx', '')).upper()}"
            ins, skp, err = sync_contacts_to_site_db(
                contacts=contacts_to_sync,
                batch_id=batch_id,
                source_label=filename,
                owner_user_id=owner_user_id
            )
            total_inserted += ins
            total_skipped += skp
            total_errors += err
            logger.info(f"File {filename}: {ins} inserted, {skp} skipped from {len(contacts_to_sync)} rows.")

        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            total_errors += 1

    summary = {
        "total_files": len(valid_files),
        "total_rows_processed": total_rows,
        "total_inserted_to_site_db": total_inserted,
        "total_skipped_duplicates": total_skipped,
        "errors": total_errors
    }
    logger.info(f"Overall Excel -> Site DB Migration: {summary}")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync Teams Extractor Excel Output to Site Database")
    parser.add_argument("--folder", type=str, default=None, help="Path to output folder containing Excel files")
    parser.add_argument("--owner", type=int, default=1, help="Owner user ID")
    args = parser.parse_args()

    res = sync_excel_folder_to_site_db(output_dir=args.folder, owner_user_id=args.owner)
    print(json.dumps(res, indent=2))
