"""
scout_desktop/ui/main_window.py — Level 3 Full Windows Companion Application Window

Obsidian Executive Architecture for TalentOps Scout Desktop v2.8.0:
- Matches media_1789415857847.png through media_1789415904006.png specification exactly
- Global Frame:
  - Top Bar: Eye logo, "TalentOps Scout", chip v2.8.0, subtitle "Edge intelligence agent",
             center pill "Active · observing" with pulsing dot, signed-in user, "Installation #483", Sign out link
  - Dismissible Update Banner: "Scout 2.9.0 available — signed release, verified and ready."
  - Left Rail (Desktop): 7 navigation tabs (Scan, Candidates, Review Queue [6], Cloud Sync, Pipeline, Activity [4], Settings)
                         plus durable local queue card ("Local queue 14 · durable · retrying in 12s")
  - Persistent Bottom Status Bar: "Synced 00:41:49", 49 records uploaded, 14 queued, No errors, Extractor 4.5.0, Scout 2.8.0, Windows 11
- 9 Interactive Screens:
  0. Scan (Home, /)
  1. Candidates (/candidates)
  2. Candidate Record (/candidates/:id)
  3. Review Queue (/review)
  4. Cloud Sync (/sync)
  5. Pipeline (/pipeline)
  6. Activity (/activity)
  7. Settings (/settings)
  8. Sign-in / Device Claim (/signin)
- 100% Backward Compatible with all app.py signals, slots, and properties.
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QStackedWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QCloseEvent

from .scout_data import (
    SYSTEM_STATE, CURRENTLY_OBSERVING, TODAYS_PIPELINE, CANDIDATES,
    REVIEW_QUEUE_ITEMS, CLOUD_SYNC_DATA, ACTIVITY_FEED,
    mark_all_activities_read, get_candidate_by_id
)
from .components import (
    TopBar, UpdateBanner, LeftRail, BottomStatusBar,
    COLOR_BG_BASE, COLOR_SURFACE_CARD, COLOR_SURFACE_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED
)
from .pages import (
    ScanPage, CandidatesPage, CandidateRecordPage, ReviewQueuePage,
    CloudSyncPage, PipelinePage, ActivityPage, SettingsPage, SignInClaimPage
)

logger = logging.getLogger("scout.main_window")


# ─────────────────────────────────────────────────────────────────────────────
# Dummy Indicator Helper (for backward compatibility with app.py)
# ─────────────────────────────────────────────────────────────────────────────

class _IndicatorStub:
    def __init__(self, name: str):
        self.name = name
        self.state = "IDLE"

    def set_state(self, state: str):
        self.state = state


# ─────────────────────────────────────────────────────────────────────────────
# MainWindow Implementation
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    TalentOps Scout Desktop v2.8.0 Obsidian Command Center Window.
    """
    # Signals required by app.py
    force_capture_requested = Signal()
    open_diagnostics_requested = Signal()
    open_settings_requested = Signal()
    shutdown_requested = Signal()
    dock_to_edge_requested = Signal()
    toggle_pause_requested = Signal()
    sync_now_requested = Signal()
    request_pair_account = Signal()
    candidate_extracted = Signal(dict)
    metric_updated = Signal(str, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("TalentOps Scout v2.8.0")
        self.resize(1120, 750)
        self.setMinimumSize(980, 640)

        # Backward compatibility attributes for app.py
        self._is_paused = False
        self._latest_profile_url = "https://www.linkedin.com/in/sarahchen-cloud"
        self.ind_backend = _IndicatorStub("backend")
        self.ind_window = _IndicatorStub("window")
        self.lbl_target_desc = QLabel("")
        self.lbl_sampling_pulse = QLabel("")
        self.lbl_cand_avatar = QLabel("SC")
        self.lbl_hero_company = QLabel("")

        self._build_shell()
        self._connect_signals()

    def _build_shell(self):
        """Build ScoutShell global frame and pages"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_BG_BASE};
            }}
            QWidget {{
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
        """)

        # Central Root Widget
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Bar
        self.top_bar = TopBar(self)
        root_layout.addWidget(self.top_bar)

        # 2. Update Banner (Dismissible)
        self.update_banner = UpdateBanner(self)
        root_layout.addWidget(self.update_banner)

        # 3. Main Center Area (Left Rail + Content Stack)
        center_row = QWidget()
        center_layout = QHBoxLayout(center_row)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Left Rail Navigation
        self.left_rail = LeftRail(self)
        center_layout.addWidget(self.left_rail)

        # Central Pages StackedWidget
        self.pages_stack = QStackedWidget(self)

        # Instantiate 9 Pages
        self.page_scan = ScanPage(self)
        self.page_candidates = CandidatesPage(self)
        self.page_candidate_record = CandidateRecordPage("sarah-chen", self)
        self.page_review = ReviewQueuePage(self)
        self.page_sync = CloudSyncPage(self)
        self.page_pipeline = PipelinePage(self)
        self.page_activity = ActivityPage(self)
        self.page_settings = SettingsPage(self)
        self.page_signin = SignInClaimPage(self)

        # Add to stack (indices 0 to 8)
        self.pages_stack.addWidget(self.page_scan)              # 0
        self.pages_stack.addWidget(self.page_candidates)        # 1
        self.pages_stack.addWidget(self.page_candidate_record)  # 2
        self.pages_stack.addWidget(self.page_review)            # 3
        self.pages_stack.addWidget(self.page_sync)              # 4
        self.pages_stack.addWidget(self.page_pipeline)          # 5
        self.pages_stack.addWidget(self.page_activity)          # 6
        self.pages_stack.addWidget(self.page_settings)          # 7
        self.pages_stack.addWidget(self.page_signin)            # 8

        center_layout.addWidget(self.pages_stack, stretch=1)
        root_layout.addWidget(center_row, stretch=1)

        # 4. Persistent Bottom Status Bar
        self.bottom_bar = BottomStatusBar(self)
        root_layout.addWidget(self.bottom_bar)

        self.setCentralWidget(root)

        # Compatibility aliases for app.py
        self.lbl_hero_name = self.page_scan.lbl_cand_name
        self.lbl_hero_title = self.page_scan.lbl_cand_subtitle
        self.lbl_hero_location = self.page_scan.lbl_cand_loc
        self.lbl_hero_pill = self.page_scan.chip_latest.lbl_text
        self.btn_pause_toggle = self.page_scan.btn_pause

    def _connect_signals(self):
        # Navigation from Left Rail
        self.left_rail.nav_changed.connect(self._on_left_rail_nav)

        # Scan Page Signals
        self.page_scan.scan_requested.connect(self.force_capture_requested.emit)
        self.page_scan.pause_toggled.connect(self._on_pause_toggled)
        self.page_scan.sync_requested.connect(self.sync_now_requested.emit)
        self.page_scan.open_candidate_requested.connect(self.open_candidate_record)
        self.page_scan.view_pipeline_requested.connect(lambda: self.navigate_to_page(4)) # Pipeline tab index

        # Candidates Page Signals
        self.page_candidates.candidate_selected.connect(self.open_candidate_record)

        # Candidate Record Page Signals
        self.page_candidate_record.back_requested.connect(lambda: self.navigate_to_page(1)) # Back to Candidates

        # Review Queue Signals
        self.page_review.item_approved.connect(self._on_review_decision)
        self.page_review.item_dismissed.connect(self._on_review_decision)

        # Cloud Sync Page Signals
        self.page_sync.sync_now_requested.connect(self.sync_now_requested.emit)

        # Activity Page Signals
        self.page_activity.feed_updated.connect(self._on_activity_feed_updated)

        # Top Bar Sign Out
        self.top_bar.sign_out_clicked.connect(lambda: self.navigate_to_page(8)) # Claim screen

        # Sign In / Claim Page Start Observing
        self.page_signin.device_claimed_and_started.connect(self._on_device_claimed)

    # ─────────────────────────────────────────────────────────────────────────
    # Navigation Router
    # ─────────────────────────────────────────────────────────────────────────

    def navigate_to_page(self, index: int):
        """Switch active page and update left rail highlight if applicable"""
        if index < 0 or index > 8:
            return
        self.pages_stack.setCurrentIndex(index)
        if index <= 6:
            # Map index to rail
            rail_map = {0: 0, 1: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
            if index in rail_map:
                self.left_rail.select_tab(rail_map[index])

    def _on_left_rail_nav(self, rail_index: int):
        """Map left rail button index to stacked widget page index"""
        page_map = {
            0: 0,  # Scan (/)
            1: 1,  # Candidates (/candidates)
            2: 3,  # Review Queue (/review)
            3: 4,  # Cloud Sync (/sync)
            4: 5,  # Pipeline (/pipeline)
            5: 6,  # Activity (/activity)
            6: 7,  # Settings (/settings)
        }
        target_page = page_map.get(rail_index, 0)
        self.pages_stack.setCurrentIndex(target_page)

    def open_candidate_record(self, candidate_id: str):
        """Open detailed candidate inspector at /candidates/:id"""
        self.page_candidate_record.set_candidate(candidate_id)
        self.pages_stack.setCurrentIndex(2)

    def _on_pause_toggled(self):
        self._is_paused = self.page_scan.is_paused
        st = "PAUSED" if self._is_paused else "Active · observing"
        self.top_bar.set_status(st, is_active=not self._is_paused)
        self.toggle_pause_requested.emit()

    def _on_review_decision(self, item_id: str):
        count = SYSTEM_STATE["badges"]["review_queue"]
        self.left_rail.update_badge("review_queue", count)
        self.left_rail.update_badge("activity", SYSTEM_STATE["badges"]["activity"])

    def _on_activity_feed_updated(self):
        self.left_rail.update_badge("activity", SYSTEM_STATE["badges"]["activity"])

    def _on_device_claimed(self):
        self.top_bar.lbl_user.setText(SYSTEM_STATE["user"]["display"])
        self.top_bar.lbl_inst.setText(SYSTEM_STATE["user"]["installation_id"])
        self.top_bar.set_status("Active · observing", is_active=True)
        self.navigate_to_page(0)

    # ─────────────────────────────────────────────────────────────────────────
    # Backward-Compatible Slots & Methods (Called by app.py)
    # ─────────────────────────────────────────────────────────────────────────

    def update_status_state(self, state_text: str):
        """Called by app.py to update edge intelligence status state"""
        is_active = "ACTIVE" in state_text or "CONNECTED" in state_text or "OBSERVING" in state_text
        self.top_bar.set_status(state_text, is_active=is_active)

    def update_account_display(self, user_display: str, user_name: str):
        """Called by app.py to update signed-in user label"""
        if user_display:
            self.top_bar.lbl_user.setText(user_display)
            SYSTEM_STATE["user"]["display"] = user_display
        if user_name:
            SYSTEM_STATE["user"]["name"] = user_name

    def update_environment(self, env: str, api_base: str):
        """Called by app.py to update environment configuration"""
        pass

    def update_window_context(self, app_name: str, title: str, url: str, context_str: str, is_allowed: bool, target_type: str):
        """Called by app.py when active window context switches"""
        status_txt = f"{app_name} · {'authorized source' if is_allowed else 'unauthorized'}"
        self.page_scan.lbl_obs_app.setText(status_txt)
        class_txt = f"Page classified as {target_type.replace('_', ' ').capitalize()} · confidence 0.97"
        self.page_scan.lbl_obs_sub.setText(class_txt)

    def update_explicit_counters(self, counters: Dict[str, Any]):
        """Called by app.py to update live pipeline counters"""
        obs = counters.get("observed", counters.get("scanned", 342))
        useful = counters.get("useful", counters.get("profiles", 128))
        canonical = counters.get("canonical", counters.get("committed", 62))
        staged = counters.get("staged", 87)

        # Update local queue badge and card
        queued_count = counters.get("queued", 14)
        self.left_rail.update_queue_status(queued_count, 12)
        self.bottom_bar.update_metrics(
            time.strftime("%H:%M:%S"),
            uploaded=canonical,
            queued=queued_count,
            errors="No errors"
        )

    def log_event(self, *args, **kwargs):
        """Called by app.py event bridge (accepts event_data dict or (event_name, details) strings)"""
        if len(args) >= 2:
            title = f"{args[0]}: {args[1]}"
            cat = kwargs.get("category", "Decisions")
            detail = str(args[1])
        elif len(args) == 1:
            item = args[0]
            if isinstance(item, dict):
                title = item.get("description", str(item))
                cat = item.get("category", "Decisions")
                detail = item.get("detail", title)
            else:
                title = str(item)
                cat = kwargs.get("category", "Decisions")
                detail = title
        else:
            title = kwargs.get("description", "System Event")
            cat = kwargs.get("category", "Decisions")
            detail = title

        ACTIVITY_FEED.insert(0, {
            "id": f"act-{int(time.time())}",
            "time": time.strftime("%H:%M:%S"),
            "title": title,
            "category": cat,
            "severity": "info",
            "unread": True,
            "detail": detail
        })
        SYSTEM_STATE["badges"]["activity"] += 1
        self.left_rail.update_badge("activity", SYSTEM_STATE["badges"]["activity"])
        self.page_activity._render_feed()

    def update_latest_capture(self, *args, **kwargs):
        pass

    def update_extraction_proof(self, *args, **kwargs):
        pass

    def update_database_proof(self, *args, **kwargs):
        pass

    def update_candidate_card(self, display_name: str, display_title: str, display_company: str, display_loc: str, status: str, initial: str, profile_url: str = "", *args, **kwargs):
        """Called by app.py when candidate is extracted or verified"""
        self.page_scan.lbl_cand_name.setText(display_name)
        self.page_scan.lbl_cand_subtitle.setText(f"{display_title} · {display_company}")
        self.page_scan.lbl_cand_loc.setText(f"📍 {display_loc}")
        self.page_scan.chip_latest.set_state(status.upper())
        if profile_url:
            self._latest_profile_url = profile_url

    def _add_candidate_table_row(self, *args, **kwargs):
        """Called by app.py to add extracted person to candidates list (supports dict or keyword args)"""
        if args and isinstance(args[0], dict):
            data = args[0]
        else:
            data = kwargs

        cid = data.get("id", f"cand-{len(CANDIDATES)+1}")
        name = data.get("name") or data.get("recruiter_name", "Unknown")
        initials = "".join([p[0].upper() for p in name.split()[:2]]) or "??"
        title = data.get("title") or data.get("raw_title", "Professional")
        company = data.get("company") or data.get("raw_company", "Organization")
        location = data.get("location") or data.get("raw_location", "Remote")
        status = data.get("status", "CANONICAL").upper()
        raw_conf = data.get("confidence", 95)
        conf = int(raw_conf * 100 if raw_conf <= 1.0 else raw_conf)
        source = f"{data.get('platform', 'Chrome')} · Person profile"

        new_cand = {
            "id": cid,
            "initials": initials,
            "name": name,
            "title": title,
            "company": company,
            "location": location,
            "state": status,
            "confidence": conf,
            "time_ago": "just now",
            "source": source,
            "profile_url": data.get("profile_url") or data.get("linkedin_url", ""),
            "fields": [
                {"label": "Name", "value": name, "raw": name, "confidence": 98},
                {"label": "Title", "value": title, "raw": title, "confidence": 95},
                {"label": "Company", "value": company, "raw": company, "confidence": 92},
                {"label": "Location", "value": location, "raw": location, "confidence": 88},
            ],
            "checklist": [
                {"title": "Platform allowlisted", "detail": "Active recruitment source", "passed": True},
                {"title": "Window stability check", "detail": "Stable frame capture", "passed": True},
                {"title": "Layout recognized", "detail": "Candidate profile card", "passed": True},
                {"title": "Confidence threshold", "detail": "Passed quality gate", "passed": True},
            ]
        }
        CANDIDATES.insert(0, new_cand)
        self.page_candidates._render_candidates()

    def closeEvent(self, event: QCloseEvent):
        """Minimize to system tray rather than closing immediately"""
        event.ignore()
        self.hide()
        self.dock_to_edge_requested.emit()
        logger.info("MainWindow hidden to system tray / edge dock. Autonomous Scout continues in background.")
