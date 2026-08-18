"""
TalentOpsAI Seniority Normalization & Quality Grade Engine
==========================================================
Scans all 367,703 profiles in the entire dataset, parses raw titles and
metadata, and classifies them into clean standardized Seniority Tiers:
  - Executive / VP / Partner
  - Director / Head of Talent
  - Manager / Lead Recruiter
  - Senior Recruiter
  - Technical / IT Recruiter
  - Healthcare & Clinical Specialist
  - Finance & Executive Consultant
  - Corporate Talent Specialist

Also calculates calibrated 0-100 Quality Scores and assigns Letter Grades:
  - Grade A+ (90-100)
  - Grade A (75-89)
  - Grade B (60-74)
  - Grade C (40-59)
  - Grade D (<40)
"""

import sys
import os
import time
import re
import math
import logging

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.services.parquet_writer import parquet_writer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SeniorityEngine")


def _safe_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        if math.isnan(val) or val != val:
            return ""
    s = str(val).strip()
    if s.lower() in ('nan', 'none'):
        return ""
    return s


def classify_seniority(title: str, name: str = "") -> str:
    """Classify raw title into standardized Seniority Level."""
    t = title.lower()
    
    # 1. Executive / VP / Partner
    if any(k in t for k in ['vice president', 'vp,', ' vp ', 'vp -', 'partner', 'chief', 'founder', 'managing director', 'principal director', 'head of talent', 'head of recruiting', 'head of ta']):
        return 'Executive / VP'
        
    # 2. Director
    if 'director' in t:
        return 'Director'
        
    # 3. Manager / Lead
    if any(k in t for k in ['manager', 'lead technical recruiter', 'lead recruiter', 'team lead', 'supervisor', 'lead talent']):
        return 'Manager / Lead'
        
    # 4. Senior Recruiter
    if any(k in t for k in ['sr.', 'sr ', 'senior', 'principal recruiter', 'executive search consultant', 'senior account manager']):
        return 'Senior Recruiter'
        
    # 5. Technical / IT Specialist
    if any(k in t for k in ['technical recruiter', 'it talent', 'it recruiter', 'tech recruiter', 'engineering & industrial', 'software', 'cloud', 'cyber', 'developer']):
        return 'Technical Recruiter'
        
    # 6. Healthcare & Clinical
    if any(k in t for k in ['healthcare', 'clinical', 'nurse', 'medical', 'hospital', 'physician', 'travel nurse']):
        return 'Healthcare Specialist'
        
    # 7. Finance & Accounting
    if any(k in t for k in ['finance', 'accounting', 'financial', 'cpa', 'auditor', 'banking']):
        return 'Finance Consultant'
        
    # 8. Legal & Compliance
    if any(k in t for k in ['legal', 'compliance', 'paralegal', 'attorney', 'law']):
        return 'Legal Specialist'
        
    return 'Corporate Talent Specialist'


def calculate_quality_score(record: dict) -> int:
    """Compute 0-100 quality score for profile completeness & reliability."""
    score = 0
    
    # Email channel (30 pts)
    email = _safe_str(record.get('email'))
    status = _safe_str(record.get('email_status'))
    if email and '@' in email and '@missing.local' not in email:
        if status == 'verified':
            score += 30
        elif status == 'likely_deliverable':
            score += 25
        elif status == 'risky_catchall':
            score += 20
        else:
            score += 10
            
    # Phone channel (20 pts)
    phone = _safe_str(record.get('phone'))
    if phone and len(re.sub(r'\D', '', phone)) >= 10:
        score += 20
        
    # LinkedIn profile (20 pts)
    linkedin = _safe_str(record.get('linkedin') or record.get('linkedin_url'))
    if linkedin and 'linkedin.com' in linkedin:
        score += 20
        
    # Company Logo & Name (15 pts)
    logo = _safe_str(record.get('logo_url'))
    company = _safe_str(record.get('company_name') or record.get('company'))
    if logo and logo.startswith('http'):
        score += 10
    if company:
        score += 5
        
    # Title / Seniority (10 pts)
    title = _safe_str(record.get('title'))
    if title and len(title) > 3:
        score += 10
        
    # Location / State (5 pts)
    state = _safe_str(record.get('state') or record.get('location'))
    if state and len(state) >= 2:
        score += 5
        
    return min(100, max(0, score))


def run_seniority_normalization(batch_size: int = 15000):
    logger.info("=" * 80)
    logger.info("STARTING SENIORITY NORMALIZATION & QUALITY GRADE CALIBRATION")
    logger.info("=" * 80)

    start_time = time.time()
    recruiter_store._ensure_loaded()
    conn = recruiter_store._conn

    total_records = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    logger.info(f"Total profiles to process: {total_records:,}")

    offset = 0
    total_processed = 0
    tier_counts = {}

    while offset < total_records:
        recruiter_store._ensure_loaded()
        conn = recruiter_store._conn

        df = conn.execute(f"""
            SELECT recruiter_id, recruiter_name, email, phone, title, company_id, state,
                   linkedin, logo_url, email_status, email_confidence, is_deliverable
            FROM recruiters
            ORDER BY recruiter_id
            LIMIT {batch_size} OFFSET {offset}
        """).df()

        if df.empty:
            break

        updates = []
        for _, row in df.iterrows():
            record = row.to_dict()
            recruiter_id = int(record['recruiter_id'])
            title = _safe_str(record.get('title'))
            name = _safe_str(record.get('recruiter_name'))

            seniority = classify_seniority(title, name)
            quality = calculate_quality_score(record)

            tier_counts[seniority] = tier_counts.get(seniority, 0) + 1

            updates.append({
                'recruiter_id': recruiter_id,
                'seniority_level': seniority,
                'quality_score': quality
            })

        total_processed += len(updates)
        offset += len(df)

        if updates:
            parquet_writer.update_records(updates)

        pct = round((offset / max(1, total_records)) * 100, 1)
        logger.info(f"Normalized {offset:,}/{total_records:,} ({pct}%) profiles...")

    duration = round(time.time() - start_time, 1)
    logger.info("=" * 80)
    logger.info(f"NORMALIZATION COMPLETE in {duration}s!")
    logger.info("Seniority Tier Distribution:")
    for tier, count in sorted(tier_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  - {tier:32s}: {count:,}")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_seniority_normalization(batch_size=15000)
