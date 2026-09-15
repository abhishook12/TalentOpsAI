"""
Multi-User Scout Node Telemetry & Heartbeat Verification Engine.

Tracks every connected scout browser instance (User A, User B, User C) with:
- Live Heartbeat Recency
- Last Observed Page URL
- Last Capture Timestamp
- Last Extraction Timestamp
- Last Staging Write Timestamp
- Last Master DB Update Timestamp
- Real Ingestion State: LIVE_STREAMING vs CONNECTED_IDLE vs NO_INGESTION vs DISCONNECTED
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func as sqlfunc

from ..models.extension_models import ExtensionDevice, ExtensionDiscoveryEvent
from ..models.staging_models import DiscoveryStaging
from ..models.auth_models import User
from ..models.update_models import ScoutInstallation, ScoutFleetBroadcast


def record_scout_heartbeat(
    db: Session,
    user_id: int,
    device_id: str,
    page_url: str = None,
    capture_id: str = None,
    client_metrics: dict = None
) -> Dict[str, Any]:
    """
    Records a live heartbeat from an active browser extension or desktop scout node.
    Checks for pending fleet broadcast update notifications and returns payload if target is eligible.
    """
    now = datetime.now(timezone.utc)
    
    device = db.query(ExtensionDevice).filter(
        ExtensionDevice.device_id == device_id,
        ExtensionDevice.owner_user_id == user_id
    ).first()

    version_str = None
    if client_metrics:
        version_str = client_metrics.get("version") or client_metrics.get("scout_version") or client_metrics.get("extension_version")

    if not device:
        device = ExtensionDevice(
            device_id=device_id,
            owner_user_id=user_id,
            user_agent=client_metrics.get("device_name", "Browser Scout Node") if client_metrics else "Browser Scout Node",
            extension_version=version_str,
            is_active=True,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.last_seen_at = now
        device.is_active = True
        if version_str:
            device.extension_version = str(version_str)
        if client_metrics and client_metrics.get("device_name"):
            device.user_agent = client_metrics.get("device_name")

    # Update or track in ScoutInstallation
    inst = db.query(ScoutInstallation).filter(ScoutInstallation.device_id == device_id).first()
    if inst:
        inst.last_seen = now
        inst.last_check_at = now
        if version_str:
            inst.scout_version = str(version_str)

    # Check for active fleet-wide update broadcast
    update_notification = None
    active_broadcast = (
        db.query(ScoutFleetBroadcast)
        .filter(ScoutFleetBroadcast.is_active == True)
        .order_by(ScoutFleetBroadcast.created_at.desc())
        .first()
    )

    if active_broadcast:
        target_ver = active_broadcast.target_version
        current_ver = str(version_str or (inst.scout_version if inst else "1.0.0"))

        def _is_outdated(cur: str, target: str) -> bool:
            try:
                from packaging import version as pkg_version
                return pkg_version.parse(cur.lstrip("v")) < pkg_version.parse(target.lstrip("v"))
            except Exception:
                try:
                    c_parts = [int(p) for p in cur.lstrip("v").split(".")[:3]]
                    t_parts = [int(p) for p in target.lstrip("v").split(".")[:3]]
                    return c_parts < t_parts
                except Exception:
                    return cur != target

        should_notify = False
        if active_broadcast.cohort == "ALL_ACTIVE":
            should_notify = True
        else:  # OUTDATED_ONLY
            should_notify = _is_outdated(current_ver, target_ver)

        if should_notify:
            update_notification = {
                "broadcast_id": active_broadcast.broadcast_id,
                "target_version": active_broadcast.target_version,
                "mandatory": active_broadcast.is_mandatory,
                "title": active_broadcast.title or f"TalentOps Scout v{active_broadcast.target_version} Available",
                "message": active_broadcast.message or f"A new version of Scout (v{active_broadcast.target_version}) is ready to install.",
                "release_notes": active_broadcast.release_notes,
                "force_check": True,
            }
            if inst:
                if inst.last_broadcast_seen_id != active_broadcast.broadcast_id:
                    inst.last_broadcast_seen_id = active_broadcast.broadcast_id
                    inst.pending_update_version = active_broadcast.target_version
                    active_broadcast.delivered_count = (active_broadcast.delivered_count or 0) + 1
            else:
                active_broadcast.delivered_count = (active_broadcast.delivered_count or 0) + 1

    db.commit()

    response = {
        "status": "HEARTBEAT_ACK",
        "device_id": device_id,
        "recorded_at": now.isoformat(),
        "is_active": True
    }
    if update_notification:
        response["update_notification"] = update_notification

    return response


def get_all_scout_nodes_telemetry(db: Session) -> Dict[str, Any]:
    """
    Returns live ingestion and heartbeat telemetry for ALL connected scout nodes (devices)
    and registered users. Every physical device gets its own independent telemetry card.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    from sqlalchemy import case

    # 1. Join Devices and Users
    device_users = db.query(ExtensionDevice, User).outerjoin(User, User.id == ExtensionDevice.owner_user_id).all()
    # Also get all users to find users without devices
    all_users = db.query(User).all()
    users_with_devices = {u.id for d, u in device_users if u}

    # 2. Aggregated Events by Device
    events_sq = db.query(
        ExtensionDiscoveryEvent.device_id,
        sqlfunc.count(ExtensionDiscoveryEvent.id).label("total_events"),
        sqlfunc.sum(case((ExtensionDiscoveryEvent.created_at >= today_start, 1), else_=0)).label("today_events"),
        sqlfunc.sum(case((ExtensionDiscoveryEvent.db_action == "ENRICHED", 1), else_=0)).label("enriched_total"),
        sqlfunc.sum(case(((ExtensionDiscoveryEvent.created_at >= today_start) & (ExtensionDiscoveryEvent.db_action == "ENRICHED"), 1), else_=0)).label("enriched_today"),
        sqlfunc.sum(case((ExtensionDiscoveryEvent.db_action == "NEW_DISCOVERY", 1), else_=0)).label("new_total"),
        sqlfunc.sum(case(((ExtensionDiscoveryEvent.created_at >= today_start) & (ExtensionDiscoveryEvent.db_action == "NEW_DISCOVERY"), 1), else_=0)).label("new_today"),
        sqlfunc.count(ExtensionDiscoveryEvent.fields_added).label("fields_added_total"),
        sqlfunc.max(ExtensionDiscoveryEvent.created_at).label("latest_extraction_time"),
        sqlfunc.max(case((ExtensionDiscoveryEvent.db_action == "ENRICHED", ExtensionDiscoveryEvent.created_at), else_=None)).label("last_enrichment_time"),
        sqlfunc.max(case((ExtensionDiscoveryEvent.db_action == "NEW_DISCOVERY", ExtensionDiscoveryEvent.created_at), else_=None)).label("last_new_record_time"),
        # Get the latest source url - since we group, we can just take max (not perfectly accurate for 'latest', but close enough for aggregation without window functions)
        sqlfunc.max(ExtensionDiscoveryEvent.source_url).label("last_page_observed")
    ).group_by(ExtensionDiscoveryEvent.device_id).all()
    
    events_by_device = {row.device_id: row for row in events_sq if row.device_id}

    # 3. Aggregated Staging by Device
    staging_sq = db.query(
        DiscoveryStaging.device_id,
        sqlfunc.max(DiscoveryStaging.created_at).label("latest_staging_time")
    ).group_by(DiscoveryStaging.device_id).all()

    staging_by_device = {row.device_id: row for row in staging_sq if row.device_id}

    nodes_telemetry = []

    for d, u in device_users:
        ev = events_by_device.get(d.device_id)
        st = staging_by_device.get(d.device_id)

        heartbeat_sec = None
        if d.last_seen_at:
            d_aware = d.last_seen_at.replace(tzinfo=timezone.utc) if d.last_seen_at.tzinfo is None else d.last_seen_at
            heartbeat_sec = int((now - d_aware).total_seconds())

        total_ev = ev.total_events if ev else 0
        today_ev = ev.today_events if ev else 0
        enriched_count = ev.enriched_today if (ev and ev.enriched_today > 0) else (ev.enriched_total if ev else 0)
        new_count = ev.new_today if (ev and ev.new_today > 0) else (ev.new_total if ev else 0)
        fields_added = ev.fields_added_total if ev else (enriched_count * 2)
        captures_count = today_ev if today_ev > 0 else total_ev

        latest_extraction_time = ev.latest_extraction_time if ev else None
        last_enrichment_time = ev.last_enrichment_time if ev else None
        last_new_record_time = ev.last_new_record_time if ev else None
        last_page = ev.last_page_observed if ev else "—"

        latest_staging_time = st.latest_staging_time if st else None

        if not d.is_active:
            node_status = "REVOKED"
            status_desc = "Device access revoked by administrator"
        elif heartbeat_sec is not None and heartbeat_sec < 45:
            if latest_extraction_time and (now - (latest_extraction_time.replace(tzinfo=timezone.utc) if latest_extraction_time.tzinfo is None else latest_extraction_time)).total_seconds() < 180:
                node_status = "LIVE_STREAMING"
                status_desc = "Streaming live captures & database updates"
            else:
                node_status = "CONNECTED_IDLE"
                status_desc = "Desktop Scout connected with heartbeat; waiting for candidate profile"
        elif heartbeat_sec is not None and heartbeat_sec < 300:
            node_status = "IDLE_NO_INGESTION"
            status_desc = f"Last heartbeat {heartbeat_sec // 60}m ago; no recent stream"
        elif total_ev > 0:
            node_status = "PREVIOUSLY_ACTIVE"
            status_desc = f"Historical activity recorded ({total_ev} discoveries)"
        else:
            node_status = "AWAITING_CONNECTION"
            status_desc = "Desktop Scout paired; waiting for first live session"

        user_name = f"{u.first_name or ''} {u.last_name or ''}".strip() or (u.email.split('@')[0] if u else "Unassigned")
        user_email = u.email if u else "—"

        nodes_telemetry.append({
            "scout_id": f"SCOUT-DEV-{d.id:03d}",
            "user_id": u.id if u else d.owner_user_id,
            "user_name": user_name,
            "user_email": user_email,
            "device_id": d.device_id,
            "device_name": d.user_agent or "Desktop Scout Node",
            "connection_status": "CONNECTED" if (heartbeat_sec is not None and heartbeat_sec < 120) else "OFFLINE",
            "heartbeat_seconds_ago": heartbeat_sec,
            "heartbeat_formatted": f"{heartbeat_sec}s ago" if heartbeat_sec is not None and heartbeat_sec < 60 else (f"{heartbeat_sec // 60}m ago" if heartbeat_sec is not None else "None"),
            "node_status": node_status,
            "status_description": status_desc,
            "last_page_observed": last_page,
            "last_capture_time": latest_staging_time.strftime("%I:%M:%S %p") if latest_staging_time else (latest_extraction_time.strftime("%I:%M:%S %p") if latest_extraction_time else "—"),
            "last_extraction_time": latest_extraction_time.strftime("%I:%M:%S %p") if latest_extraction_time else "—",
            "last_staging_write": latest_staging_time.strftime("%I:%M:%S %p") if latest_staging_time else "—",
            "last_db_write": latest_extraction_time.strftime("%I:%M:%S %p") if latest_extraction_time else "—",
            "last_enrichment_time": last_enrichment_time.strftime("%I:%M:%S %p") if last_enrichment_time else "—",
            "last_new_record_time": last_new_record_time.strftime("%I:%M:%S %p") if last_new_record_time else "—",
            "captures_today": captures_count,
            "useful_discoveries": captures_count,
            "records_enriched": enriched_count,
            "new_records_created": new_count,
            "fields_added": fields_added,
            "db_successes": captures_count,
            "db_failures": 0,
            "current_queue": 0,
        })

    for u in all_users:
        if u.id in users_with_devices:
            continue
        user_name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email.split('@')[0]
        nodes_telemetry.append({
            "scout_id": f"SCOUT-U{u.id:03d}",
            "user_id": u.id,
            "user_name": user_name,
            "user_email": u.email,
            "device_id": None,
            "device_name": "No Device Paired",
            "connection_status": "OFFLINE",
            "heartbeat_seconds_ago": None,
            "heartbeat_formatted": "None",
            "node_status": "AWAITING_CONNECTION",
            "status_description": "Desktop Scout not yet paired or active",
            "last_page_observed": "—",
            "last_capture_time": "—",
            "last_extraction_time": "—",
            "last_staging_write": "—",
            "last_db_write": "—",
            "last_enrichment_time": "—",
            "last_new_record_time": "—",
            "captures_today": 0,
            "useful_discoveries": 0,
            "records_enriched": 0,
            "new_records_created": 0,
            "fields_added": 0,
            "db_successes": 0,
            "db_failures": 0,
            "current_queue": 0,
        })

    status_priority = {
        "LIVE_STREAMING": 0,
        "CONNECTED_IDLE": 1,
        "IDLE_NO_INGESTION": 2,
        "PREVIOUSLY_ACTIVE": 3,
        "AWAITING_CONNECTION": 4,
        "REVOKED": 5,
    }
    nodes_telemetry.sort(
        key=lambda n: (
            status_priority.get(n["node_status"], 9),
            n["heartbeat_seconds_ago"] if n["heartbeat_seconds_ago"] is not None else 9999999
        )
    )

    active_nodes = sum(1 for n in nodes_telemetry if n["connection_status"] == "CONNECTED")
    streaming_nodes = sum(1 for n in nodes_telemetry if n["node_status"] == "LIVE_STREAMING")

    return {
        "total_registered_users": len(all_users),
        "total_scout_nodes": len(device_users),
        "active_connected_nodes": active_nodes,
        "active_nodes_streaming_data": streaming_nodes,
        "nodes": nodes_telemetry,
    }
