import os
import time
import logging
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.services.recruiter_store import recruiter_store, PARQUET_FILE
from app.services.parquet_writer import parquet_writer
from app.services.verification_state import verification_state
from app.services.domain_checker import domain_checker
from app.database import SessionLocal
from app.models.campaigns import EmailLog
from sqlalchemy import func, text

logger = logging.getLogger(__name__)

class EmailVerificationEngine:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self.batch_size = 5000
        self.cooldown_seconds = 2.0
        
    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("EmailVerificationEngine is already running.")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="EmailVerificationEngine", daemon=True)
        self._thread.start()
        
        with verification_state._lock:
            verification_state.state["is_running"] = True
            verification_state.state["is_paused"] = False
            if not verification_state.state["started_at"]:
                verification_state.state["started_at"] = datetime.now(timezone.utc).isoformat()
            verification_state.save()
            
        logger.info("EmailVerificationEngine started.")
        
    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            
        with verification_state._lock:
            verification_state.state["is_running"] = False
            verification_state.save()
            
        logger.info("EmailVerificationEngine stopped.")
        
    def pause(self):
        with verification_state._lock:
            verification_state.state["is_paused"] = True
            verification_state.save()
        logger.info("EmailVerificationEngine paused.")
        
    def resume(self):
        with verification_state._lock:
            verification_state.state["is_paused"] = False
            verification_state.save()
        logger.info("EmailVerificationEngine resumed.")
        
    def get_status(self) -> dict:
        return verification_state.get_progress()

    def _get_ordered_domains(self) -> List[str]:
        try:
            recruiter_store._ensure_loaded()
            conn = recruiter_store._conn
            query = """
            SELECT LOWER(SPLIT_PART(email, '@', 2)) as domain, COUNT(*) as cnt 
            FROM recruiters 
            WHERE email IS NOT NULL AND email != '' 
            GROUP BY domain 
            ORDER BY cnt DESC
            """
            df = conn.execute(query).df()
            return df['domain'].tolist()
        except Exception as e:
            logger.error(f"Error getting ordered domains: {e}")
            return []

    def _verify_single_email(self, recruiter_row: dict) -> dict:
        email = recruiter_row.get('email')
        if not email:
            return {
                'recruiter_id': recruiter_row['recruiter_id'],
                'email_status': 'invalid',
                'email_confidence': 0,
                'email_verified_at': datetime.now(timezone.utc).isoformat(),
                'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
                'email_source': 'Engine: Missing email'
            }
            
        email = email.lower().strip()
        local_part, _, domain = email.partition('@')
        
        confidence = 20  # Base score for existing
        source_methods = []
        
        # Stage 1 - Syntax
        is_valid_syntax, err = domain_checker.validate_syntax(email)
        if not is_valid_syntax:
            return {
                'recruiter_id': recruiter_row['recruiter_id'],
                'email_status': 'invalid',
                'email_confidence': 0,
                'email_verified_at': datetime.now(timezone.utc).isoformat(),
                'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
                'email_source': f'Engine: Syntax Invalid ({err})'
            }
        source_methods.append('Syntax')
            
        # Stage 2 - Domain
        domain_res = domain_checker.check_domain(domain)
        if domain_res.is_disposable:
            return {
                'recruiter_id': recruiter_row['recruiter_id'],
                'email_status': 'invalid',
                'email_confidence': 5,
                'email_verified_at': datetime.now(timezone.utc).isoformat(),
                'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
                'email_source': 'Engine: Disposable domain'
            }
            
        if domain_res.has_mx:
            confidence += 30
            source_methods.append('MX')
        else:
            confidence -= 20
            source_methods.append('No-MX')
            
        if domain_res.is_parked:
            confidence = 10
            source_methods.append('Parked')
            
        # Stage 3 - Company Correlation (Skipped for performance unless necessary, doing simple check)
        # Assumed logic: if domain is not free, give a small bump for corporate email
        if not domain_res.is_free_provider and domain_res.has_mx and not domain_res.is_parked:
            confidence += 15
            source_methods.append('Corporate')
            
        # Stage 4 - Deliverability heuristics
        if domain_checker.is_role_account(local_part):
            confidence -= 10
            source_methods.append('Role')
            
        if domain_res.is_free_provider:
            confidence -= 5
            source_methods.append('Free')
            
        # Stage 5 - Historical from PostgreSQL
        db = SessionLocal()
        try:
            delivered = db.query(func.count(EmailLog.log_id)).filter(
                EmailLog.recipient_email == email,
                EmailLog.status == 'delivered'
            ).scalar() or 0
            
            replied = db.query(func.count(EmailLog.log_id)).filter(
                EmailLog.recipient_email == email,
                EmailLog.status == 'replied'
            ).scalar() or 0
            
            bounced = db.query(func.count(EmailLog.log_id)).filter(
                EmailLog.recipient_email == email,
                EmailLog.status == 'bounced'
            ).scalar() or 0
            
            if replied > 0:
                confidence += 30
                source_methods.append('Historical-Reply')
            elif delivered > 0:
                confidence += 20
                source_methods.append('Historical-Delivered')
                
            if bounced > 0:
                confidence -= 50
                source_methods.append('Historical-Bounced')
        except Exception as e:
            logger.error(f"DB Error checking history for {email}: {e}")
        finally:
            db.close()
            
        # Stage 6 - SMTP Mailbox Ping (only for emails with confidence >= 50)
        # Probes the actual mailbox via RCPT TO handshake without sending email
        smtp_probed = False
        if confidence >= 50:
            try:
                from app.services.smtp_prober import smtp_prober
                probe_result = smtp_prober.probe_mailbox(email)
                if probe_result.smtp_code > 0:  # Got a real SMTP response
                    confidence += probe_result.confidence_delta
                    smtp_probed = True
                    if probe_result.mailbox_exists and not probe_result.is_catchall:
                        source_methods.append('SMTP-Verified')
                    elif probe_result.is_catchall:
                        source_methods.append('SMTP-CatchAll')
                    elif probe_result.smtp_code in (550, 551, 552, 553):
                        source_methods.append('SMTP-Rejected')
                    elif probe_result.is_greylisted:
                        source_methods.append('SMTP-Greylisted')
            except Exception as e:
                logger.debug(f"SMTP probe skipped for {email}: {e}")

        # Stage 7 - Scoring
        confidence = max(0, min(100, confidence))
        
        if confidence >= 90:
            status = 'verified'
        elif confidence >= 70:
            status = 'likely_valid'
        elif confidence >= 50:
            status = 'needs_monitoring'
        elif confidence >= 30:
            status = 'suspicious'
        elif confidence >= 1:
            status = 'likely_invalid'
        else:
            status = 'invalid'
            
        return {
            'recruiter_id': recruiter_row['recruiter_id'],
            'email_status': status,
            'email_confidence': confidence,
            'email_verified_at': datetime.now(timezone.utc).isoformat(),
            'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
            'email_source': f"Engine: {','.join(source_methods)}"
        }

    def _run(self):
        try:
            domains = self._get_ordered_domains()
            logger.info(f"Engine starting to process {len(domains)} domains.")
            
            state = verification_state.get_progress()
            completed_domains = set(state.get("completed_domains", []))
            
            # Count total pending roughly by subtracting processed from 2M
            recruiter_store._ensure_loaded()
            total_count_query = "SELECT COUNT(*) FROM recruiters"
            total_records = recruiter_store._conn.cursor().execute(total_count_query).fetchone()[0]
            
            with verification_state._lock:
                verification_state.state["total_pending"] = max(0, total_records - verification_state.state["total_processed"])
            
            for domain in domains:
                if self._stop_event.is_set():
                    break
                    
                # Handle Pausing
                while verification_state.get_progress().get("is_paused", False):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1.0)
                    
                if domain in completed_domains:
                    continue
                    
                with verification_state._lock:
                    verification_state.state["current_domain"] = domain
                    
                batch_offset = 0
                last_recruiter_id = 0
                domain_failed = False
                while True:
                    if self._stop_event.is_set():
                        break
                        
                    start_time = time.time()
                    
                    # Fetch batch of recruiters for this domain
                    query = f"""
                    SELECT recruiter_id, email
                    FROM recruiters 
                    WHERE LOWER(SPLIT_PART(email, '@', 2)) = ? 
                    LIMIT ? OFFSET ?
                    """
                    # parquet_writer reloads RecruiterStore after each write, so never
                    # retain a DuckDB connection across a persisted batch.
                    recruiter_store._ensure_loaded()
                    df = recruiter_store._conn.cursor().execute(query, [domain, self.batch_size, batch_offset]).df()
                    
                    if df.empty:
                        break # Done with this domain
                        
                    updates = []
                    for _, row in df.iterrows():
                        if self._stop_event.is_set():
                            break
                        recruiter_dict = row.to_dict()
                        update = self._verify_single_email(recruiter_dict)
                        updates.append(update)
                        
                    if updates:
                        try:
                            # Apply updates atomically to Parquet
                            parquet_writer.update_records(updates)
                            
                            duration = time.time() - start_time
                            for update in updates:
                                verification_state.mark_email_processed(
                                    update['email_status'], update['email_confidence']
                                )
                            verification_state.mark_batch_complete(domain, len(updates), duration)
                            logger.info(f"Batch completed: {len(updates)} emails for @{domain} in {duration:.1f}s")
                            
                            with verification_state._lock:
                                verification_state.state["total_pending"] = max(0, verification_state.state["total_pending"] - len(updates))
                        except Exception as e:
                            logger.error(f"Failed to write batch updates: {e}")
                            verification_state.add_error(f"Write batch failed for {domain}: {str(e)}")
                            domain_failed = True
                            break

                    last_recruiter_id = int(df['recruiter_id'].max())
                    batch_offset += self.batch_size
                    
                    if len(df) < self.batch_size:
                        break # Domain finished
                        
                    time.sleep(self.cooldown_seconds)

                # A domain is resumable only after its final successful batch. A
                # failed write leaves it pending for the next manually started run.
                if not domain_failed and not self._stop_event.is_set():
                    verification_state.mark_domain_complete(domain, last_recruiter_id)
                    
            logger.info("Verification Engine completed all domains.")
            
        except Exception as e:
            logger.error(f"Fatal error in verification thread: {e}")
            verification_state.add_error(f"Fatal engine error: {str(e)}")
        finally:
            with verification_state._lock:
                verification_state.state["is_running"] = False
                verification_state.save()

verification_engine = EmailVerificationEngine()
