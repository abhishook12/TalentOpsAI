import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from ..models.models import RecruiterEmail, MailIntelTracking, DomainReputation

logger = logging.getLogger(__name__)

def extract_domain(email: str) -> str:
    try:
        return email.split("@")[1].lower().strip()
    except IndexError:
        return ""

def process_delivery_event(db: Session, email_str: str, event_type: str, campaign_id: int = None, reason: str = None):
    """
    event_type can be: 'delivered', 'hard_bounce', 'soft_bounce', 'replied'
    """
    email_str = email_str.lower().strip()
    domain = extract_domain(email_str)
    
    if not domain:
        return

    # Update Domain Reputation
    # UPSERT pattern for domain reputation
    stmt = insert(DomainReputation).values(
        domain=domain,
        total_sent=1 if event_type in ['delivered', 'hard_bounce', 'soft_bounce'] else 0,
        total_delivered=1 if event_type == 'delivered' else 0,
        total_bounced=1 if event_type in ['hard_bounce', 'soft_bounce'] else 0,
        total_replied=1 if event_type == 'replied' else 0
    )
    
    update_dict = {
        'updated_at': datetime.now(timezone.utc)
    }
    
    if event_type in ['delivered', 'hard_bounce', 'soft_bounce']:
        update_dict['total_sent'] = DomainReputation.total_sent + 1
    if event_type == 'delivered':
        update_dict['total_delivered'] = DomainReputation.total_delivered + 1
    if event_type in ['hard_bounce', 'soft_bounce']:
        update_dict['total_bounced'] = DomainReputation.total_bounced + 1
    if event_type == 'replied':
        update_dict['total_replied'] = DomainReputation.total_replied + 1
        
    stmt = stmt.on_conflict_do_update(
        index_elements=['domain'],
        set_=update_dict
    )
    db.execute(stmt)
    
    # After upsert, recalculate score
    db.flush()
    dr = db.query(DomainReputation).filter(DomainReputation.domain == domain).first()
    if dr and dr.total_sent > 0:
        dr.reputation_score = (dr.total_delivered / dr.total_sent) * 100.0
    
    # Update RecruiterEmail & MailIntelTracking
    rec_email = db.query(RecruiterEmail).filter(RecruiterEmail.email == email_str).first()
    if not rec_email:
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
        tracking.hard_bounce_count += 1
        tracking.flag_reason = reason or "Hard Bounce"
        score_change = -50
    elif event_type == 'soft_bounce':
        tracking.last_bounce_at = now
        tracking.soft_bounce_count += 1
        score_change = -5
        
    # Update confidence
    new_score = rec_email.confidence_score + score_change
    new_score = max(0, min(100, new_score)) # Clamp between 0-100
    rec_email.confidence_score = new_score
    
    # Update Status based on confidence
    if event_type == 'hard_bounce' and tracking.hard_bounce_count >= 2:
        rec_email.status = 'invalid'
    else:
        if new_score >= 95:
            rec_email.status = 'verified'
        elif new_score >= 80:
            rec_email.status = 'likely_valid'
        elif new_score >= 60:
            rec_email.status = 'needs_monitoring'
        elif new_score >= 30:
            rec_email.status = 'suspicious'
        else:
            rec_email.status = 'invalid'

    db.commit()

