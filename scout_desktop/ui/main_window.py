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
    TopBar, StatusStrip, UpdateBanner, LeftRail, BottomStatusBar,
    COLOR_BG_BASE, COLOR_SURFACE_CARD, COLOR_SURFACE_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED
)
from .pages import (
    ScanPage, CandidatesPage, CandidateRecordPage, ReviewQueuePage,
    CloudSyncPage, PipelinePage, ActivityPage, SettingsPage, SignInClaimPage
)
from scout_desktop.version import __version__, EXTRACTOR_VERSION, APP_DISPLAY_NAME

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


class _CompatCounter:
    def __init__(self, value: str = "0"):
        self.value = str(value)

    def setText(self, val: str):
        self.value = str(val)

    def text(self) -> str:
        return self.value


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
        self.setWindowTitle(APP_DISPLAY_NAME)
        
        # Responsive geometry: Constrain within available work area above Windows taskbar
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(1120, avail.width() - 24)
            h = min(720, avail.height() - 48)
            self.resize(w, h)
            self.move(avail.x() + (avail.width() - w) // 2, avail.y() + (avail.height() - h) // 2)
        else:
            self.resize(1120, 700)
        self.setMinimumSize(880, 520)

        # Backward compatibility attributes for app.py
        self._is_paused = False
        self._latest_profile_url = "https://www.linkedin.com/in/sarahchen-cloud"
        self._activity_feed_dirty = False
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
            QMainWindow, QWidget#ScoutCentralRoot, QWidget#ScoutCenterRow, QStackedWidget#ScoutPagesStack {{
                background-color: {COLOR_BG_BASE};
            }}
            QWidget {{
                color: {COLOR_TEXT_PRIMARY};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
                background-color: {COLOR_BG_BASE};
                border: none;
            }}
            QScrollBar:vertical {{
                background: #0E0E0E;
                width: 8px;
                border: none;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #2A2A2A;
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #444748;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: #0E0E0E;
                height: 8px;
                border: none;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: #2A2A2A;
                min-width: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #444748;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0;
            }}
        """)

        # Central Root Widget
        root = QWidget()
        root.setObjectName("ScoutCentralRoot")
        root.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        root.setAutoFillBackground(True)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Bar
        self.top_bar = TopBar(self)
        root_layout.addWidget(self.top_bar)

        # 2. Status Strip (Command Line / Telemetry) - matches Stitch design
        status_strip_container = QWidget()
        status_strip_container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        ss_layout = QHBoxLayout(status_strip_container)
        ss_layout.setContentsMargins(16, 8, 16, 4)
        self.status_strip = StatusStrip(self)
        ss_layout.addWidget(self.status_strip)
        root_layout.addWidget(status_strip_container)

        # 3. Update Banner (Dismissible)
        self.update_banner = UpdateBanner(self)
        root_layout.addWidget(self.update_banner)

        # 3. Main Center Area (Left Rail + Content Stack)
        center_row = QWidget()
        center_row.setObjectName("ScoutCenterRow")
        center_row.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        center_layout = QHBoxLayout(center_row)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Left Rail Navigation
        self.left_rail = LeftRail(self)
        center_layout.addWidget(self.left_rail)

        # Central Pages StackedWidget
        self.pages_stack = QStackedWidget(self)
        self.pages_stack.setObjectName("ScoutPagesStack")
        self.pages_stack.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.pages_stack.setAutoFillBackground(True)

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
        self.lbl_cand_avatar = self.page_scan.lbl_avatar
        self.btn_pause_toggle = self.page_scan.btn_pause

        # Counter compatibility proxies
        self._compat_counters = {
            "captured": _CompatCounter(),
            "analyzed": _CompatCounter(),
            "useful": _CompatCounter(),
            "staged": _CompatCounter(),
            "matched": _CompatCounter(),
            "new": _CompatCounter(),
            "enriched": _CompatCounter(),
            "db_updates": _CompatCounter(),
            "purged": _CompatCounter(),
            "observed": _CompatCounter(),
            "fields_added": _CompatCounter(),
            "buffer": _CompatCounter(),
        }
        self.c_captured = self._compat_counters["captured"]
        self.c_analyzed = self._compat_counters["analyzed"]
        self.c_useful = self._compat_counters["useful"]
        self.c_staged = self._compat_counters["staged"]
        self.c_matched = self._compat_counters["matched"]
        self.c_new = self._compat_counters["new"]
        self.c_enriched = self._compat_counters["enriched"]
        self.c_db_updates = self._compat_counters["db_updates"]
        self.c_purged = self._compat_counters["purged"]
        self.c_observed = self._compat_counters["observed"]
        self.c_fields_added = self._compat_counters["fields_added"]
        self.c_buffer = self._compat_counters["buffer"]

    def _connect_signals(self):
        # Navigation from Left Rail
        self.left_rail.nav_changed.connect(self._on_left_rail_nav)
        self.left_rail.update_center_requested.connect(self.show_update_center)

        # Scan Page Signals
        self.page_scan.scan_requested.connect(self.force_capture_requested.emit)
        self.page_scan.pause_toggled.connect(self._on_pause_toggled)
        self.page_scan.sync_requested.connect(self.sync_now_requested.emit)
        self.page_scan.open_candidate_requested.connect(self.open_candidate_record)
        self.page_scan.view_pipeline_requested.connect(lambda: self.navigate_to_page(5)) # Pipeline tab index

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

        # Top Bar Sign Out, Update Center & Notifications
        self.top_bar.sign_out_clicked.connect(lambda: self.navigate_to_page(8)) # Claim screen
        self.top_bar.update_center_requested.connect(self.show_update_center)
        self.top_bar.notifications_requested.connect(self.show_notifications)

        # Settings Page Check Updates Action
        self.page_settings.check_updates_requested.connect(self.show_update_center)

        # Sign In / Claim Page Start Observing
        self.page_signin.device_claimed_and_started.connect(self._on_device_claimed)

    def set_backend_services(self, backend_client=None, updater=None):
        """Sets references to backend services for update and notification dialogs."""
        self.backend_client = backend_client
        self.updater = updater

    def show_update_center(self):
        """Opens Version & Update Center Dialog."""
        try:
            from .notifications_window import UpdateCenterDialog
            dlg = UpdateCenterDialog(
                backend_client=getattr(self, "backend_client", None),
                updater=getattr(self, "updater", None),
                parent=self
            )
            dlg.exec()
        except Exception as e:
            logger.error("Error opening update center dialog: %s", e)

    def show_notifications(self):
        """Opens Global Notifications & Fleet Broadcasts Dialog."""
        try:
            from .notifications_window import NotificationsDialog
            dlg = NotificationsDialog(
                backend_client=getattr(self, "backend_client", None),
                parent=self
            )
            dlg.exec()
            if hasattr(self, "top_bar"):
                self.top_bar.set_notification_badge(False)
        except Exception as e:
            logger.error("Error opening notifications dialog: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Navigation Router
    # ─────────────────────────────────────────────────────────────────────────

    def navigate_to_page(self, index: int):
        """Switch active page and update left rail highlight if applicable"""
        if index < 0 or index > 8:
            return
        self.pages_stack.setCurrentIndex(index)
        if index <= 7:
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
        if target_page == 6 and getattr(self, "_activity_feed_dirty", False):
            self.page_activity._render_feed()
            self._activity_feed_dirty = False

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
        st_upper = (state_text or "").upper()
        is_active = any(k in st_upper for k in ("ACTIVE", "SAMPLING", "CONNECTED", "OBSERVING"))
        if is_active and "PAUSE" not in st_upper:
            display_text = "Active · observing"
        elif "PAUSE" in st_upper:
            display_text = "Paused"
        elif "PENDING" in st_upper:
            display_text = "Setup required"
        else:
            display_text = "Idle · ready"
        self.top_bar.set_status(display_text, is_active=is_active)

    def update_account_display(self, user_display: str, user_name: str):
        """Called by app.py to update signed-in user label"""
        try:
            name = user_name or (user_display if user_display and not user_display.startswith("User #") else "Prashant")
            disp = f"{name} · TalentOps AI" if "·" not in name else name
            if hasattr(self.top_bar, "lbl_user"):
                self.top_bar.lbl_user.setText(disp)
            SYSTEM_STATE["user"]["display"] = disp
            SYSTEM_STATE["user"]["name"] = name
            if hasattr(self.top_bar, "lbl_node"):
                self.top_bar.lbl_node.setText("NODE: #483")
            elif hasattr(self.top_bar, "lbl_inst"):
                self.top_bar.lbl_inst.setText("Installation #483")
        except Exception as e:
            logger.debug("Error in update_account_display: %s", e)

    def update_environment(self, env: str, api_base: str):
        """Called by app.py to update environment configuration"""
        pass

    def update_window_context(self, app_name: str, title: str, url: str, context_str: str, is_allowed: bool, target_type: str):
        """Called by app.py when active window context switches"""
        status_txt = f"{app_name} · {'authorized source' if is_allowed else 'unauthorized'}"
        if hasattr(self.page_scan, "lbl_obs_app"):
            self.page_scan.lbl_obs_app.setText(status_txt)
        class_txt = f"GATE EVAL: {target_type.upper()}"
        if hasattr(self.page_scan, "lbl_gate"):
            self.page_scan.lbl_gate.setText(class_txt)
        elif hasattr(self.page_scan, "lbl_obs_sub"):
            self.page_scan.lbl_obs_sub.setText(class_txt)

    def update_explicit_counters(self, counters: Dict[str, Any]):
        """Called by app.py to update live pipeline counters"""
        obs = counters.get("observed", counters.get("scanned", 0))
        useful = counters.get("useful", counters.get("profiles", 0))
        canonical = counters.get("synced_today", counters.get("canonical", counters.get("committed", 0)))
        staged = counters.get("staged", 0)

        # Update compat proxy counters
        for key, val in counters.items():
            if hasattr(self, f"c_{key}"):
                getattr(self, f"c_{key}").value = str(val)

        # Update local queue badge and card
        queued_count = counters.get("queued", 0)
        retry_sec = 10 if queued_count > 0 else 0
        self.left_rail.update_queue_status(queued_count, retry_sec)
        self.bottom_bar.update_metrics(
            time.strftime("%H:%M:%S"),
            uploaded=canonical,
            queued=queued_count,
            errors=counters.get("errors", "No errors")
        )

        # Forward to ScanPage dynamic pipeline metrics
        if hasattr(self, "page_scan") and hasattr(self.page_scan, "update_pipeline_metrics"):
            self.page_scan.update_pipeline_metrics(counters)

    def update_process_load(
        self,
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        load_level: str = "OPTIMAL",
        state_label: str = "Optimal Execution",
        queue_pending: int = 0,
        ingress_latency_ms: float = 0.42,
        engine_state: str = "STEADY",
        protocol: str = "CANONICAL v2.9"
    ):
        """Propagate real-time process load and edge telemetry to UI components."""
        # 1. Update StatusStrip telemetry
        if hasattr(self, "status_strip"):
            self.status_strip.update_telemetry(
                engine_state=engine_state,
                proto_val=protocol,
                latency_ms=ingress_latency_ms,
                cpu_pct=cpu_percent,
                memory_mb=memory_mb,
                load_level=load_level
            )
        # 2. Update ScanPage Edge Process Load HUD
        if hasattr(self, "page_scan") and hasattr(self.page_scan, "update_process_load_hud"):
            self.page_scan.update_process_load_hud(
                cpu_pct=cpu_percent,
                mem_mb=memory_mb,
                latency_ms=ingress_latency_ms,
                queue_depth=queue_pending,
                load_level=load_level,
                state_label=state_label
            )
        # 3. Update BottomStatusBar
        if hasattr(self, "bottom_bar") and hasattr(self.bottom_bar, "update_process_load"):
            self.bottom_bar.update_process_load(cpu_percent, memory_mb, load_level)


    def log_event(self, *args, **kwargs):
        """
        Called by app.py event bridge.
        High-performance filtered event ingestion: Prevents heartbeat spam from flooding
        the UI thread, caps the activity feed to 30 items, and debounces rendering.
        """
        if len(args) >= 2:
            event_name = str(args[0])
            detail = str(args[1])
            title = f"{event_name}: {detail}"
            cat = kwargs.get("category", "Decisions")
        elif len(args) == 1:
            item = args[0]
            if isinstance(item, dict):
                title = item.get("description", str(item))
                cat = item.get("category", "Decisions")
                detail = item.get("detail", title)
                event_name = item.get("event", "EVENT")
            else:
                title = str(item)
                cat = kwargs.get("category", "Decisions")
                detail = title
                event_name = "EVENT"
        else:
            title = kwargs.get("description", "System Event")
            cat = kwargs.get("category", "Decisions")
            detail = title
            event_name = "EVENT"

        # Suppress spam telemetry from user-facing Activity Feed
        SPAM_NAMES = ("DB_SYNC_UP_TO_DATE", "WINDOW_DETECTED", "SCOUT_RESTING", "DB_SYNC_STARTED")
        if any(k in event_name for k in SPAM_NAMES) or any(k in title for k in SPAM_NAMES):
            return

        # Suppress consecutive duplicate logs (e.g. repeated TARGET_RESTING)
        if getattr(self, "_last_logged_title", None) == title:
            return
        self._last_logged_title = title

        # Choose appropriate icon & category
        icon = "•"
        sev = "info"
        if any(k in event_name for k in ("ERROR", "REJECT", "FAILED")):
            cat = "Errors"
            sev = "error"
            icon = "🛡️"
        elif any(k in event_name for k in ("WARN", "UNSTABLE", "DUPLICATE")):
            cat = "Warnings"
            sev = "warn"
            icon = "⚠️"
        elif any(k in event_name for k in ("SUCCESS", "COMMITTED", "PROMOTED", "ACCEPTED", "FOUND")):
            cat = "Decisions"
            sev = "success"
            icon = "✅"
        elif "RESTING" in event_name:
            cat = "Decisions"
            sev = "info"
            icon = "💤"

        ACTIVITY_FEED.insert(0, {
            "id": f"act-{int(time.time()*1000)%1000000}",
            "time": time.strftime("%H:%M:%S"),
            "title": title,
            "category": cat,
            "severity": sev,
            "icon": icon,
            "unread": True,
            "detail": detail
        })

        # Cap ACTIVITY_FEED to max 30 items
        while len(ACTIVITY_FEED) > 30:
            ACTIVITY_FEED.pop()

        SYSTEM_STATE["badges"]["activity"] = min(30, SYSTEM_STATE["badges"]["activity"] + 1)
        self.left_rail.update_badge("activity", SYSTEM_STATE["badges"]["activity"])

        # Throttled debounce render: ONLY re-render if user is currently looking at Activity page
        if self.pages_stack.currentIndex() == 6:
            if not hasattr(self, "_activity_render_timer"):
                self._activity_render_timer = QTimer(self)
                self._activity_render_timer.setSingleShot(True)
                self._activity_render_timer.timeout.connect(self.page_activity._render_feed)
            if not self._activity_render_timer.isActive():
                self._activity_render_timer.start(250)
        else:
            self._activity_feed_dirty = True

    def update_latest_capture(self, *args, **kwargs):
        pass

    def update_extraction_proof(self, *args, **kwargs):
        pass

    def update_database_proof(self, *args, **kwargs):
        pass

    def update_candidate_card(
        self,
        name: str = "",
        title: str = "",
        company: str = "",
        location: str = "",
        status: str = "CANONICAL",
        initial: str = "",
        profile_url: str = "",
        display_name: str = "",
        display_title: str = "",
        display_company: str = "",
        display_loc: str = "",
        *args,
        **kwargs
    ):
        """Called by app.py when candidate is extracted or verified"""
        cand_name = display_name or name or kwargs.get("canonical_name", "") or kwargs.get("recruiter_name", "") or kwargs.get("raw_name", "")
        cand_title = display_title or title or kwargs.get("current_title", "") or kwargs.get("raw_title", "")
        cand_company = display_company or company or kwargs.get("company_name", "") or kwargs.get("current_company", "") or kwargs.get("raw_company", "")
        cand_loc = display_loc or location or kwargs.get("raw_location", "")
        cand_status = (status or "CANONICAL").upper()
        p_url = profile_url or kwargs.get("linkedin_url", "")

        self.page_scan.lbl_cand_name.setText(cand_name or "Unknown Candidate")
        subtitle_parts = [p for p in (cand_title, cand_company) if p]
        self.page_scan.lbl_cand_subtitle.setText(" · ".join(subtitle_parts) if subtitle_parts else "Professional Profile")
        self.page_scan.lbl_cand_loc.setText(f"📍 {cand_loc}" if cand_loc else "📍 Location not specified")
        self.page_scan.chip_latest.set_state(cand_status)
        if p_url:
            self._latest_profile_url = p_url

        # Dynamic avatar initials
        initials = "".join([p[0].upper() for p in cand_name.split()[:2] if p]) or "??"
        if hasattr(self.page_scan, "lbl_avatar"):
            self.page_scan.lbl_avatar.setText(initials)

        # Dynamic confidence meters (normalize float 0.0-1.0 to int 0-100)
        def _to_pct(val, default_pct):
            if val is None:
                return default_pct
            try:
                f_val = float(val)
                return int(f_val * 100) if f_val <= 1.0 else int(f_val)
            except (ValueError, TypeError):
                return default_pct

        import hashlib
        fallback_id = f"cand-{hashlib.md5(cand_name.encode('utf-8')).hexdigest()[:8]}" if cand_name else "cand-active"
        cand_id = kwargs.get("id") or kwargs.get("candidate_id") or fallback_id
        self.page_scan._current_candidate_id = cand_id

        fc = kwargs.get("field_confidence") or {}
        name_conf = _to_pct(fc.get("name"), 95 if cand_name else 0)
        title_conf = _to_pct(fc.get("title"), 90 if cand_title else 0)
        comp_conf = _to_pct(fc.get("company"), 90 if cand_company else 0)
        loc_conf = _to_pct(fc.get("location"), 85 if cand_loc else 0)

        # Hard boundary: if field is missing or invalid, confidence MUST be 0
        if not cand_company:
            comp_conf = 0
        if not cand_loc:
            loc_conf = 0
        if not cand_title:
            title_conf = 0

        if hasattr(self.page_scan, "update_meters"):
            self.page_scan.update_meters(
                name=cand_name,
                title=cand_title,
                company=cand_company,
                location=cand_loc,
                name_conf=name_conf,
                title_conf=title_conf,
                comp_conf=comp_conf,
                loc_conf=loc_conf,
                cand_id=cand_id,
            )

        # Also ensure candidate is added or updated in the live Candidates table
        if cand_name and cand_name not in ("Unknown Candidate", "Professional Profile"):
            self._add_candidate_table_row(
                id=cand_id,
                name=cand_name,
                title=cand_title,
                company=cand_company,
                location=cand_loc,
                status=cand_status,
                confidence=kwargs.get("confidence", 95),
                platform=kwargs.get("platform", "Desktop Scout"),
                profile_url=p_url,
                raw_name=cand_name,
                raw_title=cand_title,
                raw_company=cand_company,
                raw_location=cand_loc,
                created_at=kwargs.get("created_at")
            )

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

        dt_str = time.strftime("%Y-%m-%d %H:%M:%S UTC")
        created_ts = data.get("created_at")
        if created_ts:
            try:
                from datetime import datetime, timezone
                dt_str = datetime.fromtimestamp(created_ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                pass

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
            "provenance": {
                "source": data.get("source") or f"Desktop Scout · {data.get('platform', 'Browser')}",
                "timestamp": dt_str,
                "extractor": f"{EXTRACTOR_VERSION} (Perceptual + DOM fusion)",
                "device": "Installation #483",
            },
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
        # Check for duplicates before inserting
        dup_index = -1
        new_prof = new_cand.get("profile_url")
        new_name = new_cand.get("name")
        new_comp = new_cand.get("company")
        
        for i, c in enumerate(CANDIDATES):
            c_prof = c.get("profile_url")
            c_name = c.get("name")
            c_comp = c.get("company")
            
            if new_prof and c_prof and new_prof == c_prof:
                dup_index = i
                break
            if new_name and c_name and new_name == c_name and new_comp and c_comp and new_comp == c_comp:
                dup_index = i
                break
                
        if dup_index >= 0:
            CANDIDATES[dup_index].update(new_cand)
        else:
            CANDIDATES.insert(0, new_cand)
            
        self.page_candidates._render_candidates()

    def closeEvent(self, event: QCloseEvent):
        """Minimize to system tray rather than closing immediately"""
        event.ignore()
        self.hide()
        self.dock_to_edge_requested.emit()
        logger.info("MainWindow hidden to system tray / edge dock. Autonomous Scout continues in background.")
