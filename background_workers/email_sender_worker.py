#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import smtplib
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from sqlalchemy import asc
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal
from backend.app.models.campaigns import (
    Campaign,
    CampaignRecruiter,
    CampaignRecruiterStatus,
    EmailTemplate,
    SequenceStep,
    ensure_campaign_tables,
)
from backend.app.models.models import Recruiter


VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


@dataclass
class WorkerStats:
    scanned: int = 0
    sent: int = 0
    mocked: int = 0
    failed: int = 0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone email sender worker for campaign sequences.")
    parser.add_argument("--loop-sleep", type=float, default=10.0, help="Seconds to sleep between polling loops.")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of due email rows to fetch per loop.")
    parser.add_argument("--rate-limit-seconds", type=float, default=3.0, help="Minimum wait between outbound sends.")
    parser.add_argument("--mode", choices=["mock", "smtp"], default=os.getenv("EMAIL_SENDER_MODE", "mock"))
    parser.add_argument("--smtp-host", default=os.getenv("SMTP_HOST"))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("SMTP_PORT", "587")))
    parser.add_argument("--smtp-username", default=os.getenv("SMTP_USERNAME"))
    parser.add_argument("--smtp-password", default=os.getenv("SMTP_PASSWORD"))
    parser.add_argument("--smtp-starttls", action="store_true", default=os.getenv("SMTP_STARTTLS", "true").lower() in {"1", "true", "yes"})
    parser.add_argument("--run-once", action="store_true")
    return parser.parse_args()


def build_logger() -> logging.Logger:
    logger = logging.getLogger("email_sender_worker")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger


def recruiter_variables(recruiter: Recruiter, campaign_row: CampaignRecruiter) -> dict[str, Any]:
    extra = {}
    if campaign_row.variables_json:
        try:
            extra = json.loads(campaign_row.variables_json)
        except json.JSONDecodeError:
            extra = {}

    first_name = (recruiter.recruiter_name or "").split(" ")[0] if recruiter.recruiter_name else ""
    return {
        "first_name": first_name,
        "full_name": recruiter.recruiter_name or "",
        "email": recruiter.email or "",
        "company_id": recruiter.company_id or "",
        "location": recruiter.location or "",
        "state": recruiter.state or "",
        "specialization": recruiter.specialization or "",
        "title": recruiter.title or "",
        **extra,
    }


def render_template(text: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables.get(key, "")
        return "" if value is None else str(value)

    return VARIABLE_PATTERN.sub(replace, text or "")


def next_step_for(campaign: Campaign, current_step: SequenceStep | None) -> SequenceStep | None:
    active_steps = sorted([step for step in campaign.sequence_steps if step.is_active], key=lambda item: item.step_order)
    if not active_steps:
        return None
    if current_step is None:
        return active_steps[0]
    for step in active_steps:
        if step.step_order > current_step.step_order:
            return step
    return None


def due_rows(db: Session, batch_size: int) -> list[CampaignRecruiter]:
    now = utcnow()
    return (
        db.query(CampaignRecruiter)
        .join(Campaign, Campaign.campaign_id == CampaignRecruiter.campaign_id)
        .filter(
            Campaign.is_active.is_(True),
            Campaign.is_archived.is_(False),
            CampaignRecruiter.status == CampaignRecruiterStatus.pending.value,
            CampaignRecruiter.next_send_at.isnot(None),
            CampaignRecruiter.next_send_at <= now,
        )
        .order_by(asc(CampaignRecruiter.next_send_at), asc(CampaignRecruiter.campaign_recruiter_id))
        .limit(batch_size)
        .all()
    )


def send_via_smtp(args: argparse.Namespace, sender_name: str | None, sender_email: str, recipient_email: str, reply_to: str | None, subject: str, body: str):
    if not args.smtp_host or not args.smtp_username or not args.smtp_password:
        raise RuntimeError("SMTP mode requires smtp host, username, and password")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    message["To"] = recipient_email
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    with smtplib.SMTP(args.smtp_host, args.smtp_port, timeout=20) as server:
        if args.smtp_starttls:
            server.starttls()
        server.login(args.smtp_username, args.smtp_password)
        server.send_message(message)


def mark_sent(db: Session, row: CampaignRecruiter, campaign: Campaign, current_step: SequenceStep):
    row.sent_count = int(row.sent_count or 0) + 1
    row.last_sent_at = utcnow()
    next_step = next_step_for(campaign, current_step)
    if next_step is None:
        row.status = CampaignRecruiterStatus.sent.value
        row.completed_at = row.completed_at or utcnow()
        row.current_step_id = None
        row.next_send_at = None
    else:
        row.status = CampaignRecruiterStatus.pending.value
        row.current_step_id = next_step.step_id
        row.next_send_at = utcnow() + timedelta(days=next_step.delay_days or 0, hours=next_step.delay_hours or 0)
    row.last_error = None
    db.add(row)


def mark_failed(db: Session, row: CampaignRecruiter, error: Exception):
    row.status = CampaignRecruiterStatus.failed.value
    row.last_error = str(error)
    db.add(row)


def process_row(db: Session, row: CampaignRecruiter, args: argparse.Namespace, logger: logging.Logger, stats: WorkerStats):
    campaign = row.campaign
    recruiter = row.recruiter
    current_step = row.current_step
    if campaign is None or recruiter is None or current_step is None:
        raise RuntimeError("Campaign row is missing campaign, recruiter, or current sequence step")

    template: EmailTemplate | None = current_step.template
    if template is None or not template.is_active:
        raise RuntimeError("Current sequence step does not have an active template")
    if not recruiter.email:
        raise RuntimeError("Recruiter is missing an email address")

    sender_email = campaign.from_email or args.smtp_username
    if not sender_email:
        raise RuntimeError("Campaign from_email is required before sending")

    variables = recruiter_variables(recruiter, row)
    subject = render_template(template.subject, variables)
    body = render_template(template.body, variables)

    if args.mode == "mock":
        logger.info("[MOCK SEND] recruiter_id=%s campaign_id=%s to=%s subject=%s", recruiter.recruiter_id, campaign.campaign_id, recruiter.email, subject)
        stats.mocked += 1
    else:
        send_via_smtp(
            args=args,
            sender_name=campaign.from_name,
            sender_email=sender_email,
            recipient_email=recruiter.email,
            reply_to=campaign.reply_to_email,
            subject=subject,
            body=body,
        )
        logger.info("[SMTP SEND] recruiter_id=%s campaign_id=%s to=%s", recruiter.recruiter_id, campaign.campaign_id, recruiter.email)

    mark_sent(db, row, campaign, current_step)
    stats.sent += 1


def main():
    args = parse_args()
    logger = build_logger()
    ensure_campaign_tables()
    stats = WorkerStats()
    last_send_time = 0.0

    logger.info("email sender worker started | mode=%s | batch_size=%s | loop_sleep=%s", args.mode, args.batch_size, args.loop_sleep)

    while True:
        try:
            with SessionLocal() as db:
                rows = due_rows(db, args.batch_size)
                stats.scanned += len(rows)

                if not rows:
                    logger.info("No pending campaign emails due right now.")
                for row in rows:
                    try:
                        elapsed = time.monotonic() - last_send_time
                        if elapsed < args.rate_limit_seconds:
                            time.sleep(args.rate_limit_seconds - elapsed)

                        process_row(db, row, args, logger, stats)
                        db.commit()
                        last_send_time = time.monotonic()
                    except Exception as row_error:
                        db.rollback()
                        logger.exception("Failed processing campaign_recruiter_id=%s", row.campaign_recruiter_id)
                        try:
                            row = db.merge(row)
                            mark_failed(db, row, row_error)
                            db.commit()
                        except Exception:
                            db.rollback()
                        stats.failed += 1

        except KeyboardInterrupt:
            logger.warning("Worker interrupted by user.")
            break
        except Exception:
            logger.exception("Top-level worker loop failure")

        logger.info(
            "loop summary | scanned=%s sent=%s mocked=%s failed=%s",
            stats.scanned,
            stats.sent,
            stats.mocked,
            stats.failed,
        )

        if args.run_once:
            break
        time.sleep(args.loop_sleep)


if __name__ == "__main__":
    main()
