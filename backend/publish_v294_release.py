import json
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.update_models import ScoutRelease
from app.services.release_signer import sign_package_hash

db = SessionLocal()
try:
    version = '2.9.4'
    channel = 'stable'
    sha256 = 'f060e23435a40fc369206b25d97e139295fe39da737361cd30d06e52f32f6cc7'
    size_bytes = 50084798
    download_url = 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe'
    pkg_sig = sign_package_hash(sha256)

    # Demote current releases on this channel
    db.query(ScoutRelease).filter(ScoutRelease.channel == channel).update({'is_current': False})

    existing = db.query(ScoutRelease).filter(ScoutRelease.version == version).first()
    if existing:
        existing.download_url = download_url
        existing.sha256 = sha256
        existing.size_bytes = size_bytes
        existing.package_signature = pkg_sig
        existing.status = 'ACTIVE'
        existing.is_current = True
        existing.is_public = True
        existing.rollout_percentage = 100
        existing.release_notes = 'TalentOps Scout v2.9.4 with Extractor v4.6.3 High-Precision Extraction Engine. Fixes URL security bypass, multi-role profile layouts, numeric corporate brands, 5-word cultural names, and compound TLD emails.'
        print(f'Updated existing release ID {existing.id}')
    else:
        new_rel = ScoutRelease(
            version=version,
            channel=channel,
            minimum_version='1.0.0',
            download_url=download_url,
            sha256=sha256,
            size_bytes=size_bytes,
            release_notes='TalentOps Scout v2.9.4 with Extractor v4.6.3 High-Precision Extraction Engine. Fixes URL security bypass, multi-role profile layouts, numeric corporate brands, 5-word cultural names, and compound TLD emails.',
            features_json=json.dumps({"new_capture_pipeline": True, "batch_upload_v2": True, "knowledge_graph_enabled": True, "ocr_daemon_enabled": True}),
            config_json=json.dumps({"poll_interval_sec": 30, "max_buffer_mb": 100, "max_buffer_images": 200, "hard_max_retention_sec": 300}),
            status='ACTIVE',
            package_signature=pkg_sig,
            rollout_percentage=100,
            is_paused=False,
            is_current=True,
            is_public=True,
            artifact='TalentOpsScoutSetup.exe',
            approved_at=datetime.now(timezone.utc)
        )
        db.add(new_rel)
        db.flush()
        print(f'Created new release ID {new_rel.id}')

    db.commit()

    active = db.query(ScoutRelease).filter(ScoutRelease.channel == 'stable', ScoutRelease.is_current == True).first()
    print(f'Active Canonical Global Release: ID {active.id}, Version: {active.version}, SHA: {active.sha256[:16]}..., Size: {active.size_bytes}')
finally:
    db.close()
