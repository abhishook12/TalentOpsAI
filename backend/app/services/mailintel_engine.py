import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..models.models import RecruiterEmail, MailIntelTracking, DomainReputation
from ..services.recruiter_store import recruiter_store
from ..services.parquet_writer import parquet_writer

logger = logging.getLogger(__name__)

def extract_domain(email: str) -> str:
    try:
        return email.split("@")[1].lower().strip()
    except IndexError:
        return ""


def _status_for_score(score: int, hard_bounce_count: int = 0) -> str:
    if hard_bounce_count >= 2:
        return 'invalid'
    if score >= 95:
        return 'verified'
    if score >= 80:
        return 'likely_valid'
    if score >= 60:
        return 'needs_monitoring'
    if score >= 30:
        return 'suspicious'
    return 'invalid'


def _sync_recruiter_parquet(email: str, status: str, confidence: int) -> None:
    """Keep the Parquet-backed MailIntel dashboard consistent with events."""
    try:
        recruiter_store._ensure_loaded()
        rows = recruiter_store._conn.cursor().execute(
            "SELECT recruiter_id FROM recruiters WHERE LOWER(email) = ?", [email]
        ).fetchall()
        if rows:
            parquet_writer.update_records([
                {
                    'recruiter_id': int(row[0]),
                    'email_status': status,
                    'email_confidence': confidence,
                    'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
                    'email_source': 'Campaign delivery event',
                }
                for row in rows
            ])
    except Exception as exc:
        # Campaign delivery remains authoritative in Postgres even if the
        # analytical Parquet projection is temporarily unavailable.
        logger.error("Could not sync MailIntel event to Parquet for %s: %s", email, exc)


def _apply_event_to_parquet(email: str, event_type: str) -> None:
    """Apply an event when no legacy RecruiterEmail row exists yet."""
    deltas = {'delivered': 5, 'replied': 30, 'hard_bounce': -50, 'soft_bounce': -5}
    try:
        recruiter_store._ensure_loaded()
        rows = recruiter_store._conn.cursor().execute(
            "SELECT recruiter_id, COALESCE(email_confidence, 0) FROM recruiters WHERE LOWER(email) = ?", [email]
        ).fetchall()
        updates = []
        for recruiter_id, current_confidence in rows:
            confidence = max(0, min(100, int(current_confidence or 0) + deltas.get(event_type, 0)))
            updates.append({
                'recruiter_id': int(recruiter_id),
                'email_status': _status_for_score(confidence),
                'email_confidence': confidence,
                'email_last_checked_at': datetime.now(timezone.utc).isoformat(),
                'email_source': 'Campaign delivery event',
            })
        if updates:
            parquet_writer.update_records(updates)
    except Exception as exc:
        logger.error("Could not apply MailIntel event to Parquet for %s: %s", email, exc)

def process_delivery_event(db: Session, email_str: str, event_type: str, campaign_id: int = None, reason: str = None):
    """
    event_type can be: 'delivered', 'hard_bounce', 'soft_bounce', 'replied'
    """
    email_str = email_str.lower().strip()
    domain = extract_domain(email_str)
    
    if not domain:
        return

    # ORM updates work with both local SQLite and production PostgreSQL.
    dr = db.get(DomainReputation, domain)
    if not dr:
        dr = DomainReputation(domain=domain, total_sent=0, total_delivered=0, total_bounced=0, total_replied=0)
        db.add(dr)
    if event_type in ['delivered', 'hard_bounce', 'soft_bounce']:
        dr.total_sent += 1
    if event_type == 'delivered':
        dr.total_delivered += 1
    if event_type in ['hard_bounce', 'soft_bounce']:
        dr.total_bounced += 1
    if event_type == 'replied':
        dr.total_replied += 1
    dr.updated_at = datetime.now(timezone.utc)
    if dr.total_sent > 0:
        dr.reputation_score = (dr.total_delivered / dr.total_sent) * 100.0
    
    # Update RecruiterEmail & MailIntelTracking
    rec_email = db.query(RecruiterEmail).filter(RecruiterEmail.email == email_str).first()
    if not rec_email:
        _apply_event_to_parquet(email_str, event_type)
        return
        
    tracking = db.query(MailIntelTracking).filter(MailIntelTracking.email_id == rec_email.id).first()
    if not tracking:
        tracking = MailIntelTracking(email_id=rec_email.id)
        db.add(tracking)
        
    tracking.last_campaign_id = campaign_id
    now = datetime.now(timezone.utc)
    
    score_change = 0
    
    if event_type == 'delivered':
        tracking.last_delivery_at = now
        score_change = 5
    elif event_type == 'replied':
        tracking.last_reply_at = now
        score_change = 30
    elif event_type == 'hard_bounce':
        tracking.last_bounce_at = now
        tracking.hard_bounce_count = (tracking.hard_bounce_count or 0) + 1
        tracking.flag_reason = reason or "Hard Bounce"
        score_change = -50
    elif event_type == 'soft_bounce':
        tracking.last_bounce_at = now
        tracking.soft_bounce_count = (tracking.soft_bounce_count or 0) + 1
        score_change = -5
        
    # Update confidence
    new_score = rec_email.confidence_score + score_change
    new_score = max(0, min(100, new_score)) # Clamp between 0-100
    rec_email.confidence_score = new_score
    
    rec_email.status = _status_for_score(new_score, tracking.hard_bounce_count or 0)
    _sync_recruiter_parquet(email_str, rec_email.status, new_score)
