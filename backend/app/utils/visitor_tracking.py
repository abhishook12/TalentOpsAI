import logging
from datetime import datetime
from sqlalchemy.orm import Session
from user_agents import parse
from ..models.models import VisitorSession

logger = logging.getLogger(__name__)

def upsert_visitor_session(
    db: Session,
    session_id: str,
    ip_address: str = None,
    user_agent_str: str = None,
    user_email: str = None,
    is_page_view: bool = False,
    is_action: bool = False,
    is_error: bool = False,
    time_on_page: int = 0
):
    if not session_id:
        return
        
    session_id = session_id.strip()
    
    # Try to find existing
    v_session = db.query(VisitorSession).filter(VisitorSession.session_id == session_id).first()
    
    if not v_session:
        # Create new
        browser, os, device = "Unknown", "Unknown", "Unknown"
        if user_agent_str:
            try:
                parsed_ua = parse(user_agent_str)
                browser = f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}".strip()
                os = f"{parsed_ua.os.family} {parsed_ua.os.version_string}".strip()
                device = parsed_ua.device.family
            except Exception as e:
                logger.warning(f"Failed to parse user agent: {e}")
                
        # Basic GeoIP placeholder (will need external service for real data)
        # We can implement ip-api.com here or leave as placeholder
        city, country = "Unknown", "Unknown"
        
        v_session = VisitorSession(
            session_id=session_id,
            user_email=user_email,
            ip_address=ip_address,
            city=city,
            country=country,
            browser=browser,
            os=os,
            device=device,
            total_page_views=1 if is_page_view else 0,
            total_actions=1 if is_action else 0,
            total_errors=1 if is_error else 0,
            idle_time_seconds=time_on_page or 0
        )
        db.add(v_session)
    else:
        # Update existing
        if user_email and not v_session.user_email:
            v_session.user_email = user_email
            
        if is_page_view:
            v_session.total_page_views = (v_session.total_page_views or 0) + 1
        if is_action:
            v_session.total_actions = (v_session.total_actions or 0) + 1
        if is_error:
            v_session.total_errors = (v_session.total_errors or 0) + 1
            
        if time_on_page:
            v_session.idle_time_seconds = (v_session.idle_time_seconds or 0) + time_on_page
            
        # Update ended_at to now to track active session length
        v_session.ended_at = datetime.utcnow()
        
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert VisitorSession: {e}")
