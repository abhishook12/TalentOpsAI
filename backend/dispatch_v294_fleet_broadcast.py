"""
backend/dispatch_v294_fleet_broadcast.py — Dispatches Global Fleet Broadcast for Scout v2.9.4

Actions:
1. Deactivates any stale broadcasts.
2. Creates active ScoutFleetBroadcast for v2.9.4 targeting ALL devices globally.
3. Sets pending_update_version='2.9.4' on all registered installations.
4. Creates global Notification visible in the web notification drawer for all users.
5. Invalidates backend node caches.
"""

from datetime import datetime, timezone
import json
from app.database import SessionLocal
from app.models.update_models import ScoutFleetBroadcast, ScoutInstallation, ScoutRelease
from app.models.models import Notification
from app.services.scout_node_service import invalidate_active_broadcast_cache, invalidate_scout_nodes_cache

db = SessionLocal()
try:
    target_version = "2.9.4"
    now = datetime.now(timezone.utc)
    broadcast_id = f"BCST-{now.strftime('%Y%m%d%H%M%S')}"

    # 1. Deactivate old broadcasts
    old_broadcasts = db.query(ScoutFleetBroadcast).filter(ScoutFleetBroadcast.is_active == True).all()
    for b in old_broadcasts:
        b.is_active = False
        print(f"Deactivated old broadcast: {b.broadcast_id} (target: {b.target_version})")

    # 2. Update installations to flag pending update
    installations = db.query(ScoutInstallation).all()
    targeted_count = len(installations)
    for inst in installations:
        inst.update_status = "UPDATE_AVAILABLE"
        inst.pending_update_version = target_version
        inst.last_update_check = now

    # 3. Create fresh active Fleet Broadcast
    new_broadcast = ScoutFleetBroadcast(
        broadcast_id=broadcast_id,
        target_version=target_version,
        cohort="ALL_ACTIVE",
        is_mandatory=False,
        title=f"TalentOps Scout v{target_version} Production Release Live",
        message=f"TalentOps Scout v{target_version} is now available globally across all nodes. Includes hardened URL security, multi-role profile factorization, and numeric corporate brand intelligence.",
        release_notes="Hardened extraction pipeline, URL security gate, multi-role LinkedIn profile layout support, numeric company branding support, cultural name support.",
        is_active=True,
        targeted_count=targeted_count if targeted_count > 0 else 1,
        delivered_count=0,
        acknowledged_count=0,
        created_at=now,
    )
    db.add(new_broadcast)

    # 4. Insert global Notification for Web Dashboard users
    notif = Notification(
        title=f"Scout Desktop v{target_version} Global Update Live",
        message=f"All Scout nodes globally have been provisioned for v{target_version}. Upgraded extraction pipeline is now active.",
        type="update",
        user_id=None,
        read=False,
        created_at=now,
    )
    db.add(notif)

    db.commit()
    invalidate_active_broadcast_cache()
    invalidate_scout_nodes_cache()

    print(f"\nSUCCESS: Dispatched Global Fleet Broadcast {broadcast_id} for v{target_version}")
    print(f"Targeted Installations: {targeted_count}")
    print(f"Global Web Notification created.")
finally:
    db.close()
