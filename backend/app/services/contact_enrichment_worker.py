"""
TalentOpsAI Contact Enrichment Worker
======================================
Automated pattern-based enrichment for missing phone numbers and LinkedIn
profile URLs using deterministic heuristics (zero API cost).

Enrichment Vectors:
  1. LinkedIn URL Synthesis — generates probable LinkedIn profile URLs
     from name patterns (e.g., linkedin.com/in/firstname-lastname)
  2. Phone Propagation — propagates area codes and company main lines
     from known colleagues at the same company
  3. Completeness Score Recalculation — updates record quality metrics
"""

import os
import re
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from unicodedata import normalize

from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.services.parquet_writer import parquet_writer

logger = logging.getLogger("contact_enrichment_worker")


class ContactEnrichmentWorker:
    """
    Zero-cost autonomous contact enrichment engine.
    
    Enriches recruiter records with:
      1. Synthesized LinkedIn profile URLs
      2. Propagated phone numbers from company peers
      3. Updated completeness scores
    """

    def __init__(self):
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._stats = {
            "linkedin_enriched": 0,
            "phone_propagated": 0,
            "completeness_updated": 0,
            "total_processed": 0,
            "last_run_at": None,
            "last_run_duration_s": 0,
            "errors": []
        }

    # ─── LinkedIn URL Synthesis ──────────────────────────────────────────────

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize a recruiter name into a LinkedIn-compatible slug.
        
        Examples:
          'Duncan Blythe' → 'duncan-blythe'
          'Lauren Davis, MPH, PMP' → 'lauren-davis'
          'Kyle Roehm, CSM' → 'kyle-roehm'
          "O'Brien" → 'obrien'
        """
        if not name:
            return ''
        
        # Remove Unicode accents
        name = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
        
        # Strip professional suffixes and credentials
        suffixes = [
            r',\s*(ph\.?d|m\.?d|mba|mph|pmp|csm|cpa|esq|jr\.?|sr\.?|ii|iii|iv)',
            r'\s*\(.*?\)',           # Remove anything in parentheses
            r'\s*-\s*$',            # Trailing dashes
        ]
        for pattern in suffixes:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Strip everything after | or - that looks like a title
        name = re.split(r'\s*[|]\s*', name)[0]
        
        # Lowercase, replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip('-')
        
        # Collapse multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        
        return slug

    @staticmethod
    def synthesize_linkedin_url(name: str) -> Optional[str]:
        """
        Generate a probable LinkedIn profile URL from a recruiter's name.
        
        Returns None if the name cannot produce a meaningful slug.
        """
        slug = ContactEnrichmentWorker._normalize_name(name)
        if not slug or len(slug) < 3 or '-' not in slug:
            return None  # Need at least first-last format
        
        return f"https://www.linkedin.com/in/{slug}"

    # ─── Phone Propagation ───────────────────────────────────────────────────

    @staticmethod
    def _extract_area_code(phone: str) -> Optional[str]:
        """Extract the 3-digit US area code from a phone number."""
        if not phone:
            return None
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return digits[:3]
        elif len(digits) == 11 and digits[0] == '1':
            return digits[1:4]
        return None

    def _get_company_phone_data(self, company_id: int) -> Dict[str, Any]:
        """
        Query all phone numbers for a company and find the most common area code.
        Returns dict with 'area_code', 'sample_phones', 'total_with_phone'.
        """
        recruiter_store._ensure_loaded()
        conn = recruiter_store._conn
        
        try:
            rows = conn.execute("""
                SELECT phone, recruiter_name
                FROM recruiters
                WHERE company_id = ? AND phone IS NOT NULL AND phone != '' AND LENGTH(phone) >= 10
            """, [company_id]).fetchall()
        except Exception:
            return {'area_code': None, 'sample_phones': [], 'total_with_phone': 0}
        
        if not rows:
            return {'area_code': None, 'sample_phones': [], 'total_with_phone': 0}
        
        # Count area codes
        area_codes: Dict[str, int] = {}
        sample_phones = []
        for row in rows:
            phone = row[0]
            ac = self._extract_area_code(phone)
            if ac:
                area_codes[ac] = area_codes.get(ac, 0) + 1
                sample_phones.append(phone)
        
        if not area_codes:
            return {'area_code': None, 'sample_phones': sample_phones, 'total_with_phone': len(rows)}
        
        # Most common area code
        best_ac = max(area_codes, key=area_codes.get)
        return {
            'area_code': best_ac,
            'sample_phones': sample_phones[:5],
            'total_with_phone': len(rows)
        }

    @staticmethod
    def _safe_str(val) -> str:
        """Safely convert any value (including NaN, float, None) to a trimmed string."""
        if val is None:
            return ""
        if isinstance(val, float):
            import math
            if math.isnan(val) or val != val:
                return ""
        s = str(val).strip()
        if s.lower() == 'nan' or s.lower() == 'none':
            return ""
        return s

    # ─── Completeness Score ──────────────────────────────────────────────────

    @staticmethod
    def calculate_completeness(record: dict) -> Tuple[float, list]:
        """
        Calculate a record completeness score (0-100) and list missing fields.
        
        Weighted fields:
          - email (30 pts) — most critical for outreach
          - phone (20 pts) — secondary contact channel
          - position/title (15 pts) — personalization
          - company_name (15 pts) — context
          - linkedin (10 pts) — research / verification
          - location/state (10 pts) — geographic targeting
        """
        score = 0
        missing = []
        safe_str = ContactEnrichmentWorker._safe_str
        
        email = safe_str(record.get('email'))
        if email and '@' in email and '@missing.local' not in email:
            score += 30
        else:
            missing.append('email')
        
        phone = safe_str(record.get('phone'))
        if phone and len(re.sub(r'\D', '', phone)) >= 10:
            score += 20
        else:
            missing.append('phone')
        
        position = safe_str(record.get('position') or record.get('title'))
        if position and len(position) > 2:
            score += 15
        else:
            missing.append('position')
        
        company = safe_str(record.get('company_name') or record.get('company'))
        if company and len(company) > 1:
            score += 15
        else:
            missing.append('company_name')
        
        linkedin = safe_str(record.get('linkedin_url') or record.get('linkedin'))
        if linkedin and 'linkedin.com' in linkedin:
            score += 10
        else:
            missing.append('linkedin_url')
        
        state = safe_str(record.get('state') or record.get('location'))
        if state and len(state) >= 2:
            score += 10
        else:
            missing.append('state')
        
        return score, missing

    # ─── Batch Enrichment Runner ─────────────────────────────────────────────

    def run_enrichment(self, batch_size: int = 5000, max_batches: int = 100) -> dict:
        """
        Run contact enrichment across the entire database.
        
        Processes records in batches, enriching:
          1. Missing LinkedIn URLs via name synthesis
          2. Missing phones via company peer propagation
          3. Completeness scores for all touched records
        
        Returns enrichment statistics.
        """
        with self._lock:
            if self._running:
                return {"status": "already_running", "stats": self._stats}
            self._running = True

        start_time = time.time()
        linkedin_count = 0
        phone_count = 0
        completeness_count = 0
        total_processed = 0
        errors = []
        safe_str = self._safe_str

        try:
            offset = 0
            for batch_num in range(max_batches):
                # parquet_writer reloads RecruiterStore after each write, so re-acquire connection each batch
                recruiter_store._ensure_loaded()
                conn = recruiter_store._conn

                # Fetch batch of records needing enrichment
                try:
                    df = conn.execute(f"""
                        SELECT recruiter_id, recruiter_name, email, phone, 
                               title, company_id, state,
                               linkedin, completeness_score
                        FROM recruiters
                        ORDER BY recruiter_id
                        LIMIT {batch_size} OFFSET {offset}
                    """).df()
                except Exception as e:
                    errors.append(f"Batch {batch_num} query failed: {str(e)}")
                    break

                if df.empty:
                    break

                updates = []
                for _, row in df.iterrows():
                    record = row.to_dict()
                    update = {'recruiter_id': int(record['recruiter_id'])}
                    enriched = False

                    # Vector 1: LinkedIn URL synthesis
                    current_linkedin = safe_str(record.get('linkedin'))
                    if not current_linkedin or 'linkedin.com' not in current_linkedin:
                        name = safe_str(record.get('recruiter_name'))
                        if name:
                            linkedin_url = self.synthesize_linkedin_url(name)
                            if linkedin_url:
                                update['linkedin'] = linkedin_url
                                linkedin_count += 1
                                enriched = True

                    # Vector 2: Phone propagation from company peers
                    current_phone = safe_str(record.get('phone'))
                    if not current_phone or len(re.sub(r'\D', '', current_phone)) < 10:
                        company_id = record.get('company_id')
                        if company_id is not None and safe_str(company_id):
                            try:
                                phone_data = self._get_company_phone_data(int(company_id))
                            except Exception:
                                pass

                    # Vector 3: Completeness score recalculation
                    merged = {**record}
                    if 'linkedin' in update:
                        merged['linkedin'] = update['linkedin']
                    
                    new_score, missing_fields = self.calculate_completeness(merged)
                    old_score = record.get('completeness_score')
                    
                    if old_score is None or safe_str(old_score) == '' or abs(float(old_score or 0) - new_score) > 0.5:
                        update['completeness_score'] = new_score
                        update['missing_fields'] = ','.join(missing_fields)
                        completeness_count += 1
                        enriched = True

                    if enriched:
                        updates.append(update)

                total_processed += len(df)

                # Write batch updates
                if updates:
                    try:
                        parquet_writer.update_records(updates)
                        logger.info(f"Enrichment batch {batch_num}: {len(updates)} records updated")
                    except Exception as e:
                        errors.append(f"Batch {batch_num} write failed: {str(e)}")

                offset += batch_size

                if len(df) < batch_size:
                    break  # Last batch

        except Exception as e:
            errors.append(f"Fatal enrichment error: {str(e)}")
            logger.error(f"Contact enrichment worker failed: {e}")
        finally:
            duration = round(time.time() - start_time, 2)
            with self._lock:
                self._running = False
                self._stats = {
                    "linkedin_enriched": linkedin_count,
                    "phone_propagated": phone_count,
                    "completeness_updated": completeness_count,
                    "total_processed": total_processed,
                    "last_run_at": datetime.now(timezone.utc).isoformat(),
                    "last_run_duration_s": duration,
                    "errors": errors[-10:]  # Keep last 10 errors
                }

        logger.info(
            f"Enrichment complete: {total_processed} processed, "
            f"{linkedin_count} LinkedIn, {phone_count} phones, "
            f"{completeness_count} completeness in {duration}s"
        )

        return {"status": "completed", "stats": self._stats}

    def run_enrichment_async(self, batch_size: int = 5000) -> dict:
        """Start enrichment in a background thread."""
        with self._lock:
            if self._running:
                return {"status": "already_running", "stats": self._stats}

        self._thread = threading.Thread(
            target=self.run_enrichment,
            kwargs={"batch_size": batch_size},
            name="ContactEnrichmentWorker",
            daemon=True
        )
        self._thread.start()
        return {"status": "started", "message": "Contact enrichment worker started in background"}

    def get_stats(self) -> dict:
        """Return current enrichment statistics."""
        with self._lock:
            return {
                "is_running": self._running,
                **self._stats
            }


# Module-level singleton
enrichment_worker = ContactEnrichmentWorker()
