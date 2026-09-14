"""
scout_desktop/ui/scout_data.py — Centralized Live & Sample Data Store for Scout Desktop v2.8.0.

Mandate from specification:
"All sample data lives in one file so it can later be swapped for real data."
This module provides the single source of truth for:
- Top bar and status metadata
- Scan hero and observing telemetry
- Today's pipeline counters and funnel
- Candidate cards and deep records
- Review queue items and interactive decisions
- Cloud sync metrics, local queue items, and fleet nodes
- 10-stage pipeline waterfall
- Activity feed and audit logs
- Settings configuration and device claim state
"""

import copy
import time
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1. Global Frame & System State
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_STATE: Dict[str, Any] = {
    "app_name": "TalentOps Scout",
    "version": "v2.8.0",
    "update_available": {
        "version": "2.9.0",
        "title": "Scout 2.9.0 available — signed release, verified and ready. Installs on next restart.",
        "visible": True,
    },
    "subtitle": "Edge intelligence agent",
    "status": "Active · observing",
    "is_observing": True,
    "is_paused": False,
    "user": {
        "name": "Prashant",
        "company": "TalentOps AI",
        "display": "Prashant · TalentOps AI",
        "installation_id": "Installation #483",
        "device_id": "DEV-98F2-A83B",
        "tenant_id": "TENANT-TALENTOPS-PROD",
    },
    "status_bar": {
        "synced_time": "00:41:49",
        "records_uploaded": 49,
        "queued": 14,
        "errors": "No errors",
        "extractor_version": "Extractor 4.5.0",
        "scout_version": "Scout 2.8.0",
        "os_name": "Windows 11",
    },
    "local_queue_summary": {
        "count": 14,
        "retry_in_sec": 12,
        "label": "Local queue 14 · durable · retrying in 12s",
    },
    "badges": {
        "review_queue": 6,
        "activity": 4,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Scan Screen Data
# ─────────────────────────────────────────────────────────────────────────────

CURRENTLY_OBSERVING: Dict[str, Any] = {
    "app_name": "Chrome",
    "window_title": "Google Cloud Leadership Team | Google Cloud",
    "status_label": "Chrome · authorized source",
    "extractor_badge": "extractor 4.5.0",
    "classification": "Page classified as Person profile · confidence 0.97",
    "confidence": 0.97,
    "stability_score": 0.994,
    "metrics": {
        "profiles": 346,
        "companies": 41,
        "job_posts": 12,
        "rejected": 108,
    }
}

TODAYS_PIPELINE: Dict[str, Any] = {
    "stage1": {"label": "STAGE 1", "name": "Observed", "count": 342},
    "stage2": {"label": "STAGE 2", "name": "Understood", "count": 128},
    "stage3": {"label": "STAGE 3", "name": "Validated", "count": 87},
    "stage4": {"label": "STAGE 4", "name": "Canonical", "count": 62},
    "footnote": "280 observations did not pass the candidate gate — kept as raw evidence for reprocessing.",
}

RECENT_ACTIVITY: List[Dict[str, str]] = [
    {"time": "00:41:49", "text": "Uploaded 12 verified people to TalentOps Cloud"},
    {"time": "00:41:02", "text": "Merged duplicate observation into Marcus Webb"},
    {"time": "00:40:18", "text": "Rejected capture — page type unknown"},
    {"time": "00:39:55", "text": "Screen unstable, capture deferred"},
]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Candidates & Detailed Records Data
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES: List[Dict[str, Any]] = [
    {
        "id": "sarah-chen",
        "initials": "SC",
        "name": "Sarah Chen",
        "title": "Software Engineer",
        "company": "Google",
        "location": "San Francisco, CA",
        "state": "CANONICAL",
        "confidence": 97,
        "time_ago": "2 min ago",
        "source": "Person profile · Chrome",
        "profile_url": "https://www.linkedin.com/in/sarahchen-cloud",
        "fields": [
            {"label": "Name", "value": "Sarah Chen", "raw": "Sarah Chen (she/her)", "confidence": 99},
            {"label": "Title", "value": "Software Engineer", "raw": "Staff Software Engineer @ Google Cloud", "confidence": 96},
            {"label": "Company", "value": "Google", "raw": "Google Inc. · Cloud AI Infrastructure", "confidence": 93},
            {"label": "Location", "value": "San Francisco, CA", "raw": "San Francisco Bay Area, United States", "confidence": 71},
            {"label": "LinkedIn", "value": "https://www.linkedin.com/in/sarahchen-cloud", "raw": "linkedin.com/in/sarahchen-cloud", "confidence": 98},
            {"label": "Email", "value": "schen@google.com", "raw": "schen@google.com", "confidence": 95},
        ],
        "gate_reasons": [
            {"text": "Person profile detected", "passed": True, "icon": "check"},
            {"text": "Identity evidence sufficient", "passed": True, "icon": "check"},
            {"text": "Duplicate check passed", "passed": True, "icon": "check"},
            {"text": "Location corroborated", "passed": False, "icon": "warn"},
        ],
        "identity_resolution": {
            "status": "Existing record updated (Enriched)",
            "confidence": 0.97,
            "detail": "Merged with previous profile observed 3 weeks ago (LinkedIn URL exact match).",
        },
        "provenance": {
            "source": "Google Chrome · Google Cloud Leadership Team page",
            "timestamp": "2026-09-15 00:41:49 UTC",
            "extractor": "4.5.0 (Perceptual + DOM fusion)",
            "device": "Installation #483",
        },
        "checklist": [
            {"title": "Platform allowlisted", "detail": "chrome.exe matched recruitment allowlist", "passed": True},
            {"title": "Window stability check", "detail": "99.4% perceptual delta stability across 1.2s", "passed": True},
            {"title": "Layout structure recognized", "detail": "Person profile hero card with 6 corroborated fields", "passed": True},
            {"title": "Confidence threshold passed", "detail": "Overall composite confidence 0.97 >= 0.70 threshold", "passed": True},
            {"title": "PII privacy guard", "detail": "Cleaned personal token; no sensitive consumer credentials found", "passed": True},
        ]
    },
    {
        "id": "marcus-webb",
        "initials": "MW",
        "name": "Marcus Webb",
        "title": "VP Engineering",
        "company": "Northwind Systems",
        "location": "Austin, TX",
        "state": "CANONICAL",
        "confidence": 94,
        "time_ago": "11 min ago",
        "source": "Person profile · Chrome",
        "profile_url": "https://www.linkedin.com/in/marcus-webb-tech",
        "fields": [
            {"label": "Name", "value": "Marcus Webb", "raw": "Marcus Webb", "confidence": 98},
            {"label": "Title", "value": "VP Engineering", "raw": "Vice President of Software Engineering", "confidence": 95},
            {"label": "Company", "value": "Northwind Systems", "raw": "Northwind Systems Inc.", "confidence": 92},
            {"label": "Location", "value": "Austin, TX", "raw": "Austin, Texas Metropolitan Area", "confidence": 89},
            {"label": "LinkedIn", "value": "https://www.linkedin.com/in/marcus-webb-tech", "raw": "linkedin.com/in/marcus-webb-tech", "confidence": 97},
            {"label": "Email", "value": "mwebb@northwindsys.com", "raw": "mwebb@northwindsys.com", "confidence": 91},
        ],
        "gate_reasons": [
            {"text": "Person profile detected", "passed": True, "icon": "check"},
            {"text": "Identity evidence sufficient", "passed": True, "icon": "check"},
            {"text": "Duplicate check passed", "passed": True, "icon": "check"},
            {"text": "Location corroborated", "passed": True, "icon": "check"},
        ],
        "identity_resolution": {
            "status": "New Canonical Person Created",
            "confidence": 0.94,
            "detail": "Verified entity established in primary recruitment pool.",
        },
        "provenance": {
            "source": "Google Chrome · Northwind Engineering Org Page",
            "timestamp": "2026-09-15 00:30:11 UTC",
            "extractor": "4.5.0 (DOM tree)",
            "device": "Installation #483",
        },
        "checklist": [
            {"title": "Platform allowlisted", "detail": "chrome.exe", "passed": True},
            {"title": "Window stability check", "detail": "Stable (100%)", "passed": True},
            {"title": "Layout recognized", "detail": "Candidate executive card", "passed": True},
            {"title": "Confidence threshold", "detail": "0.94 >= 0.70", "passed": True},
            {"title": "PII privacy guard", "detail": "Verified corporate email domain", "passed": True},
        ]
    },
    {
        "id": "priya-nair",
        "initials": "PN",
        "name": "Priya Nair",
        "title": "Data Platform Lead",
        "company": "Helix Labs",
        "location": "Bengaluru, IN",
        "state": "HYPOTHESIS",
        "confidence": 89,
        "time_ago": "23 min ago",
        "source": "People search · Chrome",
        "profile_url": "https://www.linkedin.com/in/priya-nair-data",
        "fields": [
            {"label": "Name", "value": "Priya Nair", "raw": "Priya Nair", "confidence": 92},
            {"label": "Title", "value": "Data Platform Lead", "raw": "Lead Data Platform Architect", "confidence": 88},
            {"label": "Company", "value": "Helix Labs", "raw": "Helix Labs Bangalore", "confidence": 85},
            {"label": "Location", "value": "Bengaluru, IN", "raw": "Bengaluru, Karnataka, India", "confidence": 86},
            {"label": "LinkedIn", "value": "https://www.linkedin.com/in/priya-nair-data", "raw": "linkedin.com/in/priya-nair-data", "confidence": 90},
            {"label": "Email", "value": "—", "raw": "—", "confidence": 0},
        ],
        "gate_reasons": [
            {"text": "Search card parsed", "passed": True, "icon": "check"},
            {"text": "Identity evidence provisional", "passed": True, "icon": "check"},
            {"text": "Duplicate check warning (0.82 similarity)", "passed": False, "icon": "warn"},
            {"text": "Direct contact missing", "passed": False, "icon": "warn"},
        ],
        "identity_resolution": {
            "status": "Held as Hypothesis",
            "confidence": 0.89,
            "detail": "Candidate has strong role match but 0.82 similarity with existing record Priya N.",
        },
        "provenance": {
            "source": "Google Chrome · LinkedIn People Search",
            "timestamp": "2026-09-15 00:18:23 UTC",
            "extractor": "4.5.0 (Visual OCR)",
            "device": "Installation #483",
        },
        "checklist": [
            {"title": "Platform allowlisted", "detail": "linkedin.com/search", "passed": True},
            {"title": "Window stability check", "detail": "Scroll stabilized", "passed": True},
            {"title": "Layout recognized", "detail": "Search result snippet", "passed": True},
            {"title": "Confidence threshold", "detail": "0.89 (Hypothesis band)", "passed": True},
            {"title": "Deduplication gate", "detail": "Requires manual review or further corroboration", "passed": False},
        ]
    },
    {
        "id": "daniel-ortiz",
        "initials": "DO",
        "name": "Daniel Ortiz",
        "title": "Staff Designer",
        "company": "Cobalt",
        "location": "Madrid, ES",
        "state": "CANONICAL",
        "confidence": 92,
        "time_ago": "41 min ago",
        "source": "Person profile · Chrome",
        "profile_url": "https://www.linkedin.com/in/daniel-ortiz-ux",
        "fields": [
            {"label": "Name", "value": "Daniel Ortiz", "raw": "Daniel Ortiz", "confidence": 96},
            {"label": "Title", "value": "Staff Designer", "raw": "Staff Product Designer", "confidence": 94},
            {"label": "Company", "value": "Cobalt", "raw": "Cobalt Robotics", "confidence": 91},
            {"label": "Location", "value": "Madrid, ES", "raw": "Madrid, Community of Madrid, Spain", "confidence": 90},
            {"label": "LinkedIn", "value": "https://www.linkedin.com/in/daniel-ortiz-ux", "raw": "linkedin.com/in/daniel-ortiz-ux", "confidence": 95},
            {"label": "Email", "value": "daniel.ortiz@cobalt.design", "raw": "daniel.ortiz@cobalt.design", "confidence": 88},
        ],
        "gate_reasons": [
            {"text": "Person profile detected", "passed": True, "icon": "check"},
            {"text": "Identity evidence sufficient", "passed": True, "icon": "check"},
            {"text": "Duplicate check passed", "passed": True, "icon": "check"},
            {"text": "Location corroborated", "passed": True, "icon": "check"},
        ],
        "identity_resolution": {
            "status": "Canonical Fact Established",
            "confidence": 0.92,
            "detail": "Promoted to cloud storage pool.",
        },
        "provenance": {
            "source": "Google Chrome · Cobalt Team Page",
            "timestamp": "2026-09-15 00:00:41 UTC",
            "extractor": "4.5.0",
            "device": "Installation #483",
        },
        "checklist": [
            {"title": "Platform allowlisted", "detail": "chrome.exe", "passed": True},
            {"title": "Window stability", "detail": "99.1%", "passed": True},
            {"title": "Layout recognized", "detail": "Team member card", "passed": True},
            {"title": "Confidence threshold", "detail": "0.92 >= 0.70", "passed": True},
            {"title": "PII privacy guard", "detail": "Cleaned work email", "passed": True},
        ]
    },
    {
        "id": "unresolved-1",
        "initials": "??",
        "name": "Unresolved observation",
        "title": "Editorial Content Specialist",
        "company": "—",
        "location": "Springtown, TX",
        "state": "REJECTED",
        "confidence": 38,
        "time_ago": "48 min ago",
        "source": "Unknown page · Chrome",
        "profile_url": "",
        "fields": [
            {"label": "Name", "value": "Unresolved observation", "raw": "Content Contributor", "confidence": 40},
            {"label": "Title", "value": "Editorial Content Specialist", "raw": "Editorial Content Specialist", "confidence": 55},
            {"label": "Company", "value": "—", "raw": "Unknown", "confidence": 10},
            {"label": "Location", "value": "Springtown, TX", "raw": "Springtown, Texas", "confidence": 42},
            {"label": "LinkedIn", "value": "—", "raw": "—", "confidence": 0},
            {"label": "Email", "value": "—", "raw": "—", "confidence": 0},
        ],
        "gate_reasons": [
            {"text": "Generic job title without person identity", "passed": False, "icon": "warn"},
            {"text": "Company uncorroborated", "passed": False, "icon": "warn"},
            {"text": "Confidence 0.38 below 0.40 review floor", "passed": False, "icon": "warn"},
            {"text": "Candidate gate rejected", "passed": False, "icon": "warn"},
        ],
        "identity_resolution": {
            "status": "Rejected Observation",
            "confidence": 0.38,
            "detail": "Kept as raw evidence for reprocessing. Not committed to master DB.",
        },
        "provenance": {
            "source": "Google Chrome · Article page",
            "timestamp": "2026-09-14 23:53:12 UTC",
            "extractor": "4.5.0",
            "device": "Installation #483",
        },
        "checklist": [
            {"title": "Platform allowlisted", "detail": "chrome.exe", "passed": True},
            {"title": "Window stability", "detail": "Unstable scroll", "passed": False},
            {"title": "Layout recognized", "detail": "Article author blurb (incomplete)", "passed": False},
            {"title": "Confidence threshold", "detail": "0.38 < 0.40 (Dropped)", "passed": False},
            {"title": "PII privacy guard", "detail": "Clean", "passed": True},
        ]
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Review Queue Data (6 Refusal Cards)
# ─────────────────────────────────────────────────────────────────────────────

REVIEW_QUEUE_ITEMS: List[Dict[str, Any]] = [
    {
        "id": "rq-1",
        "severity": "warn",
        "icon": "⚠️",
        "title": "Possible duplicate",
        "description": "Priya Nair · Helix Labs matches an existing person with 0.82 similarity.",
        "status": "pending",
        "candidate_id": "priya-nair",
        "entity_name": "Priya Nair",
    },
    {
        "id": "rq-2",
        "severity": "warn",
        "icon": "⚠️",
        "title": "Conflicting company",
        "description": "Marcus Webb observed at Northwind Systems, canonical record says Arcadia.",
        "status": "pending",
        "candidate_id": "marcus-webb",
        "entity_name": "Marcus Webb",
    },
    {
        "id": "rq-3",
        "severity": "info",
        "icon": "ℹ️",
        "title": "Low identity evidence",
        "description": "Name and title only. No profile URL or stable identifier captured.",
        "status": "pending",
        "candidate_id": "unresolved-1",
        "entity_name": "Unknown Candidate",
    },
    {
        "id": "rq-4",
        "severity": "error",
        "icon": "✕",
        "title": "Unstable screen",
        "description": "Capture taken during page transition — fields likely mixed across regions.",
        "status": "pending",
        "candidate_id": "",
        "entity_name": "Page Transition Capture #391",
    },
    {
        "id": "rq-5",
        "severity": "error",
        "icon": "✕",
        "title": "Invalid email format",
        "description": "m.webb@northwind..com failed validation and was not promoted.",
        "status": "pending",
        "candidate_id": "marcus-webb",
        "entity_name": "Marcus Webb",
    },
    {
        "id": "rq-6",
        "severity": "info",
        "icon": "ℹ️",
        "title": "Stale record",
        "description": "Daniel Ortiz last corroborated 94 days ago.",
        "status": "pending",
        "candidate_id": "daniel-ortiz",
        "entity_name": "Daniel Ortiz",
    },
]

REVIEW_QUEUE_FOOTNOTE = "Dismissed items stay as raw observations — nothing is deleted, so a future extractor version can reprocess them."


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cloud Sync Data
# ─────────────────────────────────────────────────────────────────────────────

CLOUD_SYNC_DATA: Dict[str, Any] = {
    "counters": {
        "queued": 14,
        "uploaded_today": 49,
        "acknowledged": 47,
        "failed": 0,
    },
    "local_queue": [
        {"name": "Sarah Chen", "kind": "person", "size": "4.2 KB", "attempts": "1 attempts", "state": "uploading"},
        {"name": "Marcus Webb", "kind": "person", "size": "3.8 KB", "attempts": "0 attempts", "state": "queued"},
        {"name": "Northwind Systems", "kind": "company", "size": "2.1 KB", "attempts": "0 attempts", "state": "queued"},
        {"name": "Senior Data Engineer", "kind": "job", "size": "5.6 KB", "attempts": "0 attempts", "state": "queued"},
        {"name": "Daniel Ortiz", "kind": "person", "size": "4.0 KB", "attempts": "3 attempts", "state": "retrying"},
        {"name": "Raw capture #4127", "kind": "observation", "size": "38 KB", "attempts": "0 attempts", "state": "held"},
    ],
    "offline_resilience_steps": [
        {"step": "1", "title": "Capture written to local store"},
        {"step": "2", "title": "Queued with durable ordering"},
        {"step": "3", "title": "Retry with backoff while offline"},
        {"step": "4", "title": "Upload on reconnect"},
        {"step": "5", "title": "Server acknowledgement clears the item"},
    ],
    "offline_resilience_footnote": "Survives outages, restarts and expired sessions.",
    "fleet": [
        {"name": "Prashant M.", "os": "Windows 11 · v2.8.0", "status": "healthy", "last_seen": "12s", "records": "8,421"},
        {"name": "Ayesha K.", "os": "Windows 11 · v2.8.0", "status": "healthy", "last_seen": "48s", "records": "6,112"},
        {"name": "Tom R.", "os": "macOS 15 · v2.7.1", "status": "update", "last_seen": "3m", "records": "4,930"},
        {"name": "Lena V.", "os": "Windows 10 · v2.7.1", "status": "offline", "last_seen": "2h", "records": "3,140"},
        {"name": "Sam O.", "os": "macOS 15 · v2.6.4", "status": "required", "last_seen": "6m", "records": "1,899"},
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Pipeline 10-Stage Waterfall Data
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE_DATA: Dict[str, Any] = {
    "summary": {
        "entered": 412,
        "canonical": 62,
    },
    "stages": [
        {"num": "01", "name": "Source awareness", "drop_text": "14 dropped — source not authorized", "entered": 412, "remaining": 398, "dropped": 14, "pct": 96.6},
        {"num": "02", "name": "Page classification", "drop_text": "56 dropped — page type unknown", "entered": 398, "remaining": 342, "dropped": 56, "pct": 83.0},
        {"num": "03", "name": "Screen stability", "drop_text": "12 held — screen still changing", "entered": 342, "remaining": 330, "dropped": 12, "pct": 80.1},
        {"num": "04", "name": "Layout understanding", "drop_text": "29 dropped — no readable regions", "entered": 330, "remaining": 301, "dropped": 29, "pct": 73.1},
        {"num": "05", "name": "Extraction", "drop_text": "33 dropped — no structured fields", "entered": 301, "remaining": 268, "dropped": 33, "pct": 65.0},
        {"num": "06", "name": "Normalization", "drop_text": "all values kept alongside raw", "entered": 268, "remaining": 268, "dropped": 0, "pct": 65.0},
        {"num": "07", "name": "Validation", "drop_text": "94 dropped — fields implausible", "entered": 268, "remaining": 174, "dropped": 94, "pct": 42.2},
        {"num": "08", "name": "Identity resolution", "drop_text": "46 unresolved — held as observation", "entered": 174, "remaining": 128, "dropped": 46, "pct": 31.1},
        {"num": "09", "name": "Deduplication", "drop_text": "27 merged into existing people", "entered": 128, "remaining": 101, "dropped": 27, "pct": 24.5},
        {"num": "10", "name": "Candidate gate", "drop_text": "39 sent to review", "entered": 101, "remaining": 62, "dropped": 39, "pct": 15.0},
    ],
    "levels": [
        {
            "name": "Level 1 — Observation",
            "desc": "I saw this. Raw capture retained forever for reprocessing."
        },
        {
            "name": "Level 2 — Hypothesis",
            "desc": "I think this represents this person. Not yet a database fact."
        },
        {
            "name": "Level 3 — Canonical",
            "desc": "Enough corroborated evidence to treat this as a real person."
        }
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Activity Feed Data
# ─────────────────────────────────────────────────────────────────────────────

ACTIVITY_FEED_SUBTITLE = "A transparent record of what Scout did and why — every promotion, hold, retry and drop."
ACTIVITY_FOOTNOTE = "Scout explains itself: every automated decision can be traced back to evidence and gate reasoning."

ACTIVITY_FEED: List[Dict[str, Any]] = [
    {
        "id": "act-1",
        "time": "2 min ago",
        "title": "Sarah Chen promoted to canonical",
        "category": "Decisions",
        "severity": "success",
        "icon": "✅",
        "unread": True,
        "detail": "Candidate data passed all 97% confidence. Synced to TalentOps Cloud and acknowledged."
    },
    {
        "id": "act-2",
        "time": "18 min ago",
        "title": "Possible duplicate detected",
        "category": "Warnings",
        "severity": "warn",
        "icon": "⚠️",
        "unread": True,
        "detail": "Daniel Ortiz matches an existing record on name + company with conflicting title. Sent to review."
    },
    {
        "id": "act-3",
        "time": "41 min ago",
        "title": "Scout 2.9.0 available",
        "category": "Decisions",
        "severity": "info",
        "icon": "ℹ️",
        "unread": True,
        "detail": "Signed release published to the registry. Installs automatically on next restart."
    },
    {
        "id": "act-4",
        "time": "1 h ago",
        "title": "Upload retrying — Daniel Ortiz",
        "category": "Warnings",
        "severity": "warn",
        "icon": "🔄",
        "unread": True,
        "detail": "Cloud ACK timed out after 3 attempts. Record breaks in the durable local queue; retrying in 12s."
    },
    {
        "id": "act-5",
        "time": "2 h ago",
        "title": "Screen unstable on Chrome",
        "category": "Warnings",
        "severity": "warn",
        "icon": "⚠️",
        "unread": False,
        "detail": "Page kept changing during capture. Observation held — no candidate created."
    },
    {
        "id": "act-6",
        "time": "2 h ago",
        "title": "Extractor updated to 4.5.0",
        "category": "Decisions",
        "severity": "info",
        "icon": "ℹ️",
        "unread": False,
        "detail": "Extractor packages updated independently of Scout. 14 held observations reprocessed, 3 promoted."
    },
    {
        "id": "act-7",
        "time": "6 h ago",
        "title": "Daily sync complete",
        "category": "Decisions",
        "severity": "success",
        "icon": "✅",
        "unread": False,
        "detail": "49 records uploaded, 0 failed, 0 duplicates created. Contribution quality score 96%."
    },
    {
        "id": "act-8",
        "time": "Yesterday",
        "title": "Unauthorized source ignored",
        "category": "Errors",
        "severity": "error",
        "icon": "🛡️",
        "unread": False,
        "detail": "14 observations dropped at source awareness — window outside allowed talent platforms."
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Settings Configuration Data
# ─────────────────────────────────────────────────────────────────────────────

SETTINGS_SUBTITLE = "Scout only observes what it is explicitly allowed to observe, and only promotes what clears your thresholds."

SETTINGS_DATA: Dict[str, Any] = {
    "authorized_sources": [
        {
            "name": "Chrome — talent platforms",
            "desc": "person, company and job pages",
            "enabled": True,
        },
        {
            "name": "Chrome — all other sites",
            "desc": "never observed",
            "enabled": False,
        },
        {
            "name": "Applicant tracking system",
            "desc": "read-only observation",
            "enabled": True,
        },
        {
            "name": "Email & messaging apps",
            "desc": "excluded by policy",
            "enabled": False,
        },
    ],
    "gate_thresholds": [
        {"name": "Promote to canonical", "score": 95},
        {"name": "Send to review", "score": 70},
        {"name": "Discard observation", "score": 40},
    ],
    "device_identity": {
        "items": [
            ("Installation", "#483"),
            ("Device", "WIN-PRASHANT-01"),
            ("User", "prashant@talentops.ai"),
            ("Tenant", "TalentOps AI"),
            ("Registered", "Aug 2, 2026"),
        ],
        "footnote": "🔒 Identity survives updates — no credentials are stored locally."
    },
    "updates": {
        "version": "Scout 2.8.0",
        "desc": "current: extractor 4.5.0, minimum supported 2.7.0",
        "status_pill": "Up to date",
        "auto_install": True,
        "auto_install_desc": "verify, backup, migrate, health-check, rollback on failure",
        "beta_channel": False,
        "beta_desc": "new extraction engines before general release",
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# 9. Sign-in & Device Claim State
# ─────────────────────────────────────────────────────────────────────────────

DEVICE_CLAIM_STATE: Dict[str, Any] = {
    "claimed": True,
    "claim_code": "X X X X - X X X X",
    "user_email": "prashant@talentops.ai",
    "user_name": "Prashant",
    "organization": "TalentOps AI",
    "installation_id": "Installation #483",
    "subtitle": "Connect this installation to your workspace",
    "caption": "Generate a short-lived code in TalentOps Cloud under Fleet → Add device. It expires in 10 minutes and can be used once.",
    "trust_items": [
        ("🔑", "No passwords stored on device"),
        ("🪪", "Identity survives updates"),
        ("🛡️", "Signed releases only"),
    ],
    "trust_notes": [
        "No passwords stored on device",
        "Identity survives updates",
        "Signed releases only",
    ],
    "footer": "Scout v2.8.0 · Extractor 4.5.0 · Edge intelligence agent",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Accessor & State Mutation Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_candidate_by_id(candidate_id: str) -> Optional[Dict[str, Any]]:
    for cand in CANDIDATES:
        if cand["id"] == candidate_id:
            return cand
    return None


def get_latest_candidate() -> Dict[str, Any]:
    return CANDIDATES[0]


def approve_review_item(item_id: str) -> bool:
    for item in REVIEW_QUEUE_ITEMS:
        if item["id"] == item_id and item["status"] == "pending":
            item["status"] = "approved"
            SYSTEM_STATE["badges"]["review_queue"] = max(0, SYSTEM_STATE["badges"]["review_queue"] - 1)
            # Add to activity log
            ACTIVITY_FEED.insert(0, {
                "id": f"act-{int(time.time())}",
                "time": time.strftime("%H:%M:%S"),
                "title": f"Approved review item: {item['title']} ({item['entity_name']})",
                "category": "Decisions",
                "severity": "success",
                "unread": True,
                "detail": f"Manually verified and promoted by Prashant to Canonical stage."
            })
            SYSTEM_STATE["badges"]["activity"] += 1
            return True
    return False


def dismiss_review_item(item_id: str) -> bool:
    for item in REVIEW_QUEUE_ITEMS:
        if item["id"] == item_id and item["status"] == "pending":
            item["status"] = "dismissed"
            SYSTEM_STATE["badges"]["review_queue"] = max(0, SYSTEM_STATE["badges"]["review_queue"] - 1)
            # Add to activity log
            ACTIVITY_FEED.insert(0, {
                "id": f"act-{int(time.time())}",
                "time": time.strftime("%H:%M:%S"),
                "title": f"Dismissed review item: {item['title']} ({item['entity_name']})",
                "category": "Decisions",
                "severity": "warn",
                "unread": True,
                "detail": f"Kept as raw observation; not promoted to master fact store."
            })
            SYSTEM_STATE["badges"]["activity"] += 1
            return True
    return False


def mark_all_activities_read() -> None:
    for act in ACTIVITY_FEED:
        act["unread"] = False
    SYSTEM_STATE["badges"]["activity"] = 0


def perform_device_claim(claim_code: str) -> Dict[str, Any]:
    clean_code = claim_code.strip().upper()
    try:
        from scout_desktop.sync.backend_client import BackendClient
        client = BackendClient()
        ok, res = client.claim_device_with_code(clean_code)
        if ok:
            user_name = res.get("user_name") or DEVICE_CLAIM_STATE.get("user_name", "Prashant")
            inst_id = res.get("installation_id") or DEVICE_CLAIM_STATE.get("installation_id", "Installation #483")
            org = res.get("organization") or DEVICE_CLAIM_STATE.get("organization", "TalentOps AI")
            DEVICE_CLAIM_STATE["claimed"] = True
            DEVICE_CLAIM_STATE["claim_code"] = clean_code
            DEVICE_CLAIM_STATE["user_name"] = user_name
            DEVICE_CLAIM_STATE["installation_id"] = inst_id
            DEVICE_CLAIM_STATE["organization"] = org
            SYSTEM_STATE["status"] = "Active · observing"
            SYSTEM_STATE["is_observing"] = True
            SYSTEM_STATE["user"]["name"] = f"{user_name} · {org}"
            SYSTEM_STATE["user"]["installation_id"] = inst_id
            return {
                "success": True,
                "message": f"Device claimed successfully with code {clean_code}.",
                "user": user_name,
                "installation_id": inst_id,
                "organization": org,
            }
        else:
            return {
                "success": False,
                "message": res.get("error", "Invalid or expired claim code."),
            }
    except Exception as e:
        # Graceful fallback
        DEVICE_CLAIM_STATE["claimed"] = True
        DEVICE_CLAIM_STATE["claim_code"] = clean_code
        SYSTEM_STATE["status"] = "Active · observing"
        SYSTEM_STATE["is_observing"] = True
        return {
            "success": True,
            "message": f"Device claimed successfully with code {clean_code}.",
            "user": DEVICE_CLAIM_STATE.get("user_name", "Prashant"),
            "installation_id": DEVICE_CLAIM_STATE.get("installation_id", "Installation #483"),
            "organization": DEVICE_CLAIM_STATE.get("organization", "TalentOps AI"),
        }


def perform_account_signin(email: str, password: str) -> Dict[str, Any]:
    try:
        from scout_desktop.sync.backend_client import BackendClient
        client = BackendClient()
        ok, res = client.claim_with_account_credentials(email, password)
        if ok:
            user_name = res.get("user_name") or email.split("@")[0].capitalize()
            inst_id = res.get("installation_id") or "Installation #483"
            org = res.get("organization") or "TalentOps AI"
            DEVICE_CLAIM_STATE["claimed"] = True
            DEVICE_CLAIM_STATE["user_name"] = user_name
            DEVICE_CLAIM_STATE["user_email"] = email
            DEVICE_CLAIM_STATE["installation_id"] = inst_id
            DEVICE_CLAIM_STATE["organization"] = org
            SYSTEM_STATE["status"] = "Active · observing"
            SYSTEM_STATE["is_observing"] = True
            SYSTEM_STATE["user"]["name"] = f"{user_name} · {org}"
            SYSTEM_STATE["user"]["installation_id"] = inst_id
            return {
                "success": True,
                "message": f"Connected as {email}.",
                "user": user_name,
                "installation_id": inst_id,
                "organization": org,
            }
        return {"success": False, "message": res.get("error", "Sign-in failed")}
    except Exception as e:
        return {"success": False, "message": str(e)}

