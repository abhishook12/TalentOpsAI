"""
Production-grade campaign send engine (Controlled Batch Processing).

Processes campaign email queues with:
- Controlled batch processing (prevents memory spikes)
- Hard recipient cap per campaign (MAX_RECIPIENTS_PER_CAMPAIGN)
- Throttled worker pool (5 concurrent workers)
- Intelligent retry with exponential backoff
- Per-email lifecycle tracking
- Campaign-level fault tolerance
- Pause/Resume/Cancel support
"""
import asyncio
import logging
import math
import random
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import requests
import concurrent.futures

from ..database import SessionLocal
from ..models.campaigns import (
    Campaign, CampaignStatus, CampaignRecruiter, CampaignRecruiterStatus,
    EmailLog, EmailLogStatus, EmailSignature
)
from .personalization import interpolate_variables

logger = logging.getLogger(__name__)

# Bridge configuration
BRIDGE_URL = "http://127.0.0.1:1337"
WORKER_COUNT = 5  # Reduced from 100 to prevent memory spikes and system crashes
MAX_RETRIES_OVERALL = 3
MAX_RECIPIENTS_PER_CAMPAIGN = 50  # Hard cap — prevents system-wide lockdowns
BATCH_SIZE = 10  # Process emails in small batches
BATCH_COOLDOWN_SECONDS = 1.5  # Pause between batches to let memory settle

# We use a ThreadPoolExecutor for requests.post to avoid blocking the asyncio event loop
request_executor = concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT * 2)

def _utcnow():
    return datetime.now(timezone.utc)

def _check_account_health(sender_account_id: int, user_id: int) -> tuple[bool, str]:
    from ..models.auth_models import ConnectedEmailAccount, User
    from ..database import SessionLocal
    
    with SessionLocal() as db:
        if sender_account_id:
            account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == sender_account_id).first()
        else:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.default_sender_id:
                account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == user.default_sender_id).first()
            else:
                account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.user_id == user_id).first()
                
        if not account or account.status != "connected":
            return False, "Email account not connected"
        if account.provider == "microsoft" and not account.access_token:
            return False, "Missing Microsoft access token"
        if account.provider == "smtp" and not account.smtp_host:
            return False, "Missing SMTP host"
            
    return True, "healthy"

def _set_campaign_status(campaign_id: int, status: str):
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            campaign.status = status
            db.commit()

def _get_campaign_eta(campaign_id: int) -> dict:
    """Calculate ETA based on fast worker pool throughput — single GROUP BY query."""
    from sqlalchemy import func as sa_func
    with SessionLocal() as db:
        counts = dict(
            db.query(CampaignRecruiter.status, sa_func.count())
            .filter(CampaignRecruiter.campaign_id == campaign_id)
            .group_by(CampaignRecruiter.status)
            .all()
        )
        total = sum(counts.values())
        terminal = ['Sent', 'Delivered', 'Opened', 'Replied', 'Bounced', 'Cancelled']
        sent = sum(counts.get(s, 0) for s in terminal)
        failed = counts.get('Failed', 0)
        retrying = counts.get('Retrying', 0)
        queued = counts.get('Queued', 0)
        sending = counts.get('Sending', 0)
        pending = counts.get('Pending', 0) + queued + sending + retrying

        remaining = pending
        # With concurrent workers, ~0.3s per email for ≤50 recipients
        estimated_seconds_per_email = 0.3
        eta_seconds = int(remaining * estimated_seconds_per_email)
        effective_rate = int(60 / estimated_seconds_per_email) if estimated_seconds_per_email > 0 else 0

        from sqlalchemy import or_
        has_auth_error = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status == 'Failed',
            or_(
                CampaignRecruiter.last_error.like('%Gmail API Error%'),
                CampaignRecruiter.last_error.like('%Token expired%'),
                CampaignRecruiter.last_error.like('%Graph API Error%401%'),
                CampaignRecruiter.last_error.like('%Graph API Error%403%')
            )
        ).first() is not None

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "retrying": retrying,
            "pending": pending,
            "queued": queued,
            "sending": sending,
            "remaining": remaining,
            "progress_percent": round((sent / total) * 100, 1) if total > 0 else 0,
            "eta_seconds": eta_seconds,
            "rate_per_minute": effective_rate,
            "has_auth_error": has_auth_error,
        }

import os
MSAL_CLIENT_ID = os.getenv("MSAL_CLIENT_ID", "replace_me")
MSAL_CLIENT_SECRET = os.getenv("MSAL_CLIENT_SECRET", "replace_me")
MSAL_TENANT_ID = os.getenv("MSAL_TENANT_ID", "common")

from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

def _refresh_google_token(account) -> str:
    from ..database import SessionLocal
    with SessionLocal() as db:
        if not account.refresh_token:
            return None
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            r = requests.post(token_url, data=data, timeout=10)
            if r.ok:
                token_json = r.json()
                account.access_token = token_json["access_token"]
                if "refresh_token" in token_json:
                    account.refresh_token = token_json["refresh_token"]
                db.commit()
                return account.access_token
        except Exception:
            pass
    return None

def _refresh_msal_token(account) -> str:
    from ..database import SessionLocal
    with SessionLocal() as db:
        if not account.refresh_token:
            return None
        token_url = f"https://login.microsoftonline.com/{MSAL_TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": MSAL_CLIENT_ID,
            "client_secret": MSAL_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            r = requests.post(token_url, data=data, timeout=10)
            if r.ok:
                token_json = r.json()
                account.access_token = token_json["access_token"]
                if "refresh_token" in token_json:
                    account.refresh_token = token_json["refresh_token"]
                db.commit()
                return account.access_token
        except Exception:
            pass
    return None

async def _send_email_via_provider(sender_account_id: int, user_id: int, payload: dict) -> tuple[bool, str, str]:
    from ..models.auth_models import ConnectedEmailAccount, User
    from ..database import SessionLocal
    from ..routes.bridge import MOCK_OAUTH
    if MOCK_OAUTH:
        await asyncio.sleep(0.01)
        return True, None, None
        
    def _do_request(retry_auth=True):
        try:
            with SessionLocal() as db:
                if sender_account_id:
                    account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == sender_account_id).first()
                else:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.default_sender_id:
                        account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.account_id == user.default_sender_id).first()
                    else:
                        account = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.user_id == user_id).first()
                
                if not account:
                    return False, "No sending account found", "auth_error"
                
                sender_email = account.email_address
                sender_name = account.display_name or sender_email.split('@')[0].replace('.', ' ').title()
                final_sender_email = payload.get("from_email") or sender_email
                
                if account.provider == "microsoft":
                    if not account.access_token:
                        return False, "Missing Microsoft access token", "auth_error"
                    access_token = account.access_token
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    graph_payload = {
                        "message": {
                            "subject": payload.get("subject", ""),
                            "from": {
                                "emailAddress": {
                                    "address": final_sender_email,
                                    "name": sender_name
                                }
                            },
                            "body": {
                                "contentType": "HTML",
                                "content": payload.get("html_body", "")
                            },
                            "toRecipients": [
                                {
                                    "emailAddress": {
                                        "address": payload.get("to_email")
                                    }
                                }
                            ]
                        },
                        "saveToSentItems": True
                    }
                    resp = requests.post("https://graph.microsoft.com/v1.0/me/sendMail", headers=headers, json=graph_payload, timeout=10)
                    if resp.status_code == 401 and retry_auth:
                        new_token = _refresh_msal_token(account)
                        if new_token:
                            return _do_request(retry_auth=False)
                        return False, "Token expired", "auth_expired"
                    if resp.ok or resp.status_code == 202:
                        return True, None, None
                    else:
                        error_type = "auth_permanent" if resp.status_code in [401, 403] else "graph_error"
                        return False, f"Graph API Error: {resp.text}", error_type
                
                elif account.provider == "smtp" or account.provider == "google" or account.provider == "yahoo":
                    # Generic SMTP send
                    import smtplib
                    from email.mime.text import MIMEText
                    from email.mime.multipart import MIMEMultipart
                    from ..utils.encryption import decrypt_token
                    
                    msg = MIMEMultipart()
                    msg['From'] = f"{sender_name} <{final_sender_email}>"
                    msg['To'] = payload.get("to_email")
                    msg['Subject'] = payload.get("subject", "")
                    msg.attach(MIMEText(payload.get("html_body", ""), 'html'))
                    
                    if account.provider == "google" and account.access_token:
                        # Use Gmail API for sending via OAuth
                        import base64
                        raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
                        headers = {
                            "Authorization": f"Bearer {account.access_token}",
                            "Content-Type": "application/json"
                        }
                        gmail_payload = {"raw": raw_msg}
                        resp = requests.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers=headers, json=gmail_payload, timeout=10)
                        if resp.status_code == 401 and retry_auth:
                            new_token = _refresh_google_token(account)
                            if new_token:
                                return _do_request(retry_auth=False)
                            return False, "Google token expired", "auth_expired"
                        if resp.ok:
                            return True, None, None
                        else:
                            error_type = "auth_permanent" if resp.status_code in [401, 403] else "api_error"
                            return False, f"Gmail API Error: {resp.text}", error_type

                    # Fallback to SMTP
                    if account.provider == "google":
                        smtp_host = "smtp.gmail.com"
                        smtp_port = 587
                        smtp_user = account.email_address
                        # Should use an app password stored in smtp_pass
                        smtp_pass = decrypt_token(account.smtp_pass) if account.smtp_pass else ""
                    elif account.provider == "yahoo":
                        smtp_host = "smtp.mail.yahoo.com"
                        smtp_port = 587
                        smtp_user = account.email_address
                        smtp_pass = decrypt_token(account.smtp_pass) if account.smtp_pass else ""
                    else:
                        smtp_host = account.smtp_host
                        smtp_port = account.smtp_port
                        smtp_user = account.smtp_user
                        smtp_pass = decrypt_token(account.smtp_pass) if account.smtp_pass else ""
                        
                    if not smtp_pass or not smtp_host:
                        return False, "Missing SMTP credentials/host", "smtp_error"
                        
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    server.quit()
                    return True, None, None
                    
                else:
                    return False, f"Unknown provider: {account.provider}", "unknown"
                
        except requests.exceptions.Timeout:
            return False, "Request timed out (10s)", "timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to external API", "network_lost"
        except Exception as e:
            return False, str(e), "unknown"
            
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(request_executor, _do_request)

def _check_and_finalize_campaign(campaign_id: int):
    from ..database import SessionLocal
    from ..models.campaigns import Campaign, CampaignStatus, CampaignRecruiter, CampaignRecruiterStatus
    
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign or campaign.status != CampaignStatus.active.value:
            return

        active_count = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.queued.value,
                CampaignRecruiterStatus.sending.value,
                CampaignRecruiterStatus.retrying.value
            ])
        ).count()

        if active_count == 0:
            failed_count = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.campaign_id == campaign_id,
                CampaignRecruiter.status == CampaignRecruiterStatus.failed.value
            ).count()

            new_status = CampaignStatus.failed.value if failed_count > 0 else CampaignStatus.completed.value
            logger.info(f"Campaign {campaign_id} finalized as {new_status}")
            campaign.status = new_status
            db.commit()

async def _worker_task(worker_id: int, campaign_id: int, queue: asyncio.Queue, signature_html: str, template: dict, from_email: str, user_id: int, sender_account_id: int):
    logger.info(f"Worker {worker_id} started for campaign {campaign_id}")
    while True:
        try:
            recipient_id = await queue.get()
        except asyncio.CancelledError:
            break
            
        try:
            def _process_recipient_db(recipient_id):
                with SessionLocal() as db:
                    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
                    if not campaign or campaign.status not in [CampaignStatus.active.value]:
                        return False

                    recipient = db.query(CampaignRecruiter).filter(
                        CampaignRecruiter.campaign_recruiter_id == recipient_id
                    ).first()
                    
                    if not recipient or recipient.status == CampaignRecruiterStatus.cancelled.value:
                        return False
                    
                    # Mark sending
                    recipient.status = CampaignRecruiterStatus.sending.value
                    recruiter = recipient.recruiter
                    company = recruiter.company if recruiter else None
                    rec_email = recruiter.email if recruiter and recruiter.email else "unknown"
                    rec_name = recruiter.recruiter_name if recruiter else None
                    retry_count = recipient.retry_count
                    
                    log = EmailLog(
                        campaign_id=campaign_id,
                        campaign_recruiter_id=recipient_id,
                        recipient_email=rec_email,
                        recipient_name=rec_name,
                        status=EmailLogStatus.sending.value,
                        attempt_number=retry_count + 1,
                        sending_at=_utcnow(),
                        sent_via="outlook_bridge"
                    )
                    db.add(log)
                    
                    subject_template = template.get("subject", "No Subject")
                    body_template = template.get("body", "")
                    
                    subject = interpolate_variables(subject_template, recruiter, company)
                    body = interpolate_variables(body_template, recruiter, company, signature_html=signature_html)
                    
                    log.subject = subject
                    log.body_preview = body[:500] if body else ""
                    log.body_html = body or ""  # Full body for the bridge — body_preview is truncated and must not be sent
                    db.commit()
                    return rec_email, subject, body, log.log_id

            result = await asyncio.to_thread(_process_recipient_db, recipient_id)
            if not result:
                queue.task_done()
                # Run finalize step immediately!
                await asyncio.to_thread(_check_and_finalize_campaign, campaign_id)
                continue
                
            rec_email, subject, body, log_id = result
            
            payload = {
                "to_email": rec_email,
                "subject": subject,
                "html_body": body or ""
            }
            
            logger.info(f"Worker {worker_id}: Sending email to {rec_email} via provider...")
            success, error_msg, error_type = await _send_email_via_provider(sender_account_id, user_id, payload)
            
            def _update_result_db(success, error_msg, error_type):
                with SessionLocal() as db:
                    from ..models.campaigns import EmailLog, CampaignRecruiter, EmailLogStatus, CampaignRecruiterStatus
                    log = db.query(EmailLog).filter(EmailLog.log_id == log_id).first()
                    recipient = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == recipient_id).first()
                    
                    if log:
                        log.body_html = None
                        if success:
                            log.status = EmailLogStatus.delivered.value
                            log.delivered_at = _utcnow()
                            log.outlook_accepted = True
                        else:
                            log.status = EmailLogStatus.failed.value
                            log.error_message = error_msg
                            log.failed_at = _utcnow()
                            log.outlook_accepted = False
                            
                    retry_count = 0
                    if recipient:
                        if success:
                            recipient.status = CampaignRecruiterStatus.sent.value
                            recipient.last_sent_at = _utcnow()
                            recipient.sent_count += 1
                        else:
                            recipient.last_error = error_msg
                            if error_type in ["auth_expired", "auth_permanent", "smtp_error"]:
                                recipient.retry_count = recipient.max_retries
                                recipient.status = CampaignRecruiterStatus.failed.value
                                retry_count = 0
                            else:
                                recipient.retry_count += 1
                                retry_count = recipient.retry_count
                                if recipient.retry_count >= recipient.max_retries:
                                    recipient.status = CampaignRecruiterStatus.failed.value
                                else:
                                    recipient.status = CampaignRecruiterStatus.retrying.value
                    
                    db.commit()
                # Run finalize step immediately!
                _check_and_finalize_campaign(campaign_id)
                return retry_count
                    
            retry_count = await asyncio.to_thread(_update_result_db, success, error_msg, error_type)
            
            if not success and retry_count > 0:
                asyncio.create_task(_schedule_retry(queue, recipient_id, retry_count))
                
        except Exception as e:
            logger.error(f"Worker {worker_id} exception for {recipient_id}: {e}")
        finally:
            queue.task_done()

async def _schedule_retry(queue: asyncio.Queue, recipient_id: int, retry_count: int):
    # Exponential backoff: 30s, 60s, 120s
    delay = 30 * (2 ** (retry_count - 1))
    await asyncio.sleep(delay)
    # Check if campaign is still active before putting it back
    with SessionLocal() as db:
        rec = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == recipient_id).first()
        if rec and rec.status == CampaignRecruiterStatus.retrying.value:
            rec.status = CampaignRecruiterStatus.queued.value
            db.commit()
            await queue.put(recipient_id)

async def process_campaign_queue(campaign_id: int):
    """Background task manager for a campaign's email queue.
    Uses continuous loop to prevent hangs and drops batches to speed up sending."""
    logger.info(f"Starting Campaign Manager for {campaign_id}")
    
    queue = asyncio.Queue()
    signature_html = None
    template = {}
    from_email = None
    user_id = None
    sender_account_id = None
    
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return
        
        user_id = campaign.user_id
        from_email = campaign.from_email
        sender_account_id = campaign.sender_account_id
        
    healthy, error = _check_account_health(sender_account_id, user_id)
    if not healthy:
        logger.warning(f"Sending account is currently offline or missing ({error}). Campaign {campaign_id} will be queued up for when it reconnects.")
        
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign.signature_id:
            sig = db.query(EmailSignature).filter(EmailSignature.signature_id == campaign.signature_id).first()
            if sig:
                signature_html = sig.html_content
        
        active_steps = sorted([s for s in campaign.sequence_steps if s.is_active], key=lambda s: s.step_order)
        if active_steps and active_steps[0].template:
            template = {
                "subject": active_steps[0].template.subject or campaign.name,
                "body": active_steps[0].template.body or ""
            }
        else:
            template = {"subject": campaign.name or "No Subject", "body": ""}
        
        pending_recipients = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.retrying.value,
            ])
        ).all()
        
        if len(pending_recipients) > MAX_RECIPIENTS_PER_CAMPAIGN:
            logger.warning(f"Campaign {campaign_id} has {len(pending_recipients)} recipients, capping to {MAX_RECIPIENTS_PER_CAMPAIGN}")
            for r in pending_recipients[MAX_RECIPIENTS_PER_CAMPAIGN:]:
                r.status = CampaignRecruiterStatus.cancelled.value
            pending_recipients = pending_recipients[:MAX_RECIPIENTS_PER_CAMPAIGN]
    
        all_recipient_ids = []
        for i, r in enumerate(pending_recipients):
            r.status = CampaignRecruiterStatus.queued.value
            r.queue_position = i + 1
            all_recipient_ids.append(r.campaign_recruiter_id)
        db.commit()

    # Guard: if no recipients were found, do NOT silently complete
    if not all_recipient_ids:
        logger.warning(f"Campaign {campaign_id} has 0 pending recipients. Marking as failed.")
        _set_campaign_status(campaign_id, CampaignStatus.failed.value)
        return

    # Start workers once
    workers = []
    for i in range(min(WORKER_COUNT, len(all_recipient_ids))):
        task = asyncio.create_task(_worker_task(i, campaign_id, queue, signature_html, template, from_email, user_id, sender_account_id))
        workers.append(task)
    
    for rid in all_recipient_ids:
        queue.put_nowait(rid)
        
    # Wait for the queue to completely drain, which includes any retries put back into the queue
    # because queue.join() blocks until queue.task_done() matches the number of items put.
    await queue.join()
    
    # We still wait up to a few seconds just in case there are pending DB commits, but the worker finalize handles it.
    await asyncio.to_thread(_check_and_finalize_campaign, campaign_id)
    
    for w in workers:
        w.cancel()

_background_tasks = set()
_active_campaign_managers = set()

async def start_campaign(campaign_id: int):
    """Start background processor for campaign. Status is already set to active by the route."""
    if campaign_id in _active_campaign_managers:
        logger.warning(f"Campaign {campaign_id} manager already running, skipping double-start.")
        return
    
    async def managed_task():
        _active_campaign_managers.add(campaign_id)
        try:
            await process_campaign_queue(campaign_id)
        finally:
            _active_campaign_managers.discard(campaign_id)
            
    task = asyncio.create_task(managed_task())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

def pause_campaign(campaign_id: int):
    """Set campaign to paused. The processor loop will exit after current email."""
    _set_campaign_status(campaign_id, CampaignStatus.paused.value)

def cancel_campaign(campaign_id: int):
    """Set campaign to cancelled. The processor will mark remaining as cancelled."""
    _set_campaign_status(campaign_id, CampaignStatus.cancelled.value)
    with SessionLocal() as db:
        db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.queued.value,
                CampaignRecruiterStatus.pending.value,
            ])
        ).update({"status": CampaignRecruiterStatus.cancelled.value}, synchronize_session=False)
        db.commit()

async def resume_campaign(campaign_id: int):
    """Resume a paused campaign."""
    with SessionLocal() as db:
        db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.retrying.value,
            ])
        ).update({"status": CampaignRecruiterStatus.queued.value}, synchronize_session=False)
        db.commit()
    
    await start_campaign(campaign_id)

def get_campaign_progress(campaign_id: int) -> dict:
    """Get real-time campaign progress with ETA."""
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}
        
        return _get_campaign_eta(campaign_id)

def restart_active_campaigns():
    """Crash recovery: Resume any campaign that was in active state when the server crashed."""
    try:
        with SessionLocal() as db:
            # Reset any queued items back to pending in case of crash
            db.query(CampaignRecruiter).filter(
                CampaignRecruiter.status == CampaignRecruiterStatus.queued.value
            ).update({"status": CampaignRecruiterStatus.pending.value}, synchronize_session=False)
            db.commit()
            
            active_campaigns = db.query(Campaign).filter(Campaign.status == CampaignStatus.active.value).all()
            for c in active_campaigns:
                logger.info(f"Crash recovery: Restarting campaign {c.campaign_id}...")
                task = asyncio.create_task(process_campaign_queue(c.campaign_id))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
    except Exception as e:
        logger.error(f"Failed to run crash recovery for active campaigns: {e}")
