"""
scout_desktop/ui/pages.py — The 9 Obsidian Executive Screens for Scout Desktop v2.8.0.

Screens implemented:
0. ScanPage (/) — Live face, hero card, 4 metrics, action buttons, pipeline funnel, Sarah Chen card, why Scout accepted
1. CandidatesPage (/candidates) — Search, filter pills, candidate card grid, click to open record
2. CandidateRecordPage (/candidates/:id) — Deep person inspector: raw vs normalized fields, identity resolution, provenance, gate checklist
3. ReviewQueuePage (/review) — 6 refusal cards with severity icons, Approve/Dismiss actions, retention footnote
4. CloudSyncPage (/sync) — Sync now, 4 metric counters, local queue table, 5-step resilience, Fleet list
5. PipelinePage (/pipeline) — 10-stage waterfall, dropoffs, Level 1/2/3 explainer cards
6. ActivityPage (/activity) — Feed of decisions, filters (All/Unread/Decisions/Warnings/Errors), unread indicators, Mark all read
7. SettingsPage (/settings) — Authorized sources, gate confidence thresholds, device identity, versions, update toggles
8. SignInClaimPage (/signin) — Claim code entry, trust notes, interactive claim state, start-observing navigation
"""

import sys
import webbrowser
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QLineEdit,
    QSizePolicy, QProgressBar, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize, QUrl, QTimer
from PySide6.QtGui import QFont, QColor, QCursor, QDesktopServices

from .scout_data import (
    SYSTEM_STATE, CURRENTLY_OBSERVING, TODAYS_PIPELINE, RECENT_ACTIVITY,
    CANDIDATES, REVIEW_QUEUE_ITEMS, REVIEW_QUEUE_FOOTNOTE,
    CLOUD_SYNC_DATA, PIPELINE_DATA, ACTIVITY_FEED, SETTINGS_DATA,
    DEVICE_CLAIM_STATE, get_candidate_by_id, approve_review_item,
    dismiss_review_item, mark_all_activities_read, perform_device_claim,
    perform_account_signin,
    ACTIVITY_FEED_SUBTITLE, ACTIVITY_FOOTNOTE, SETTINGS_SUBTITLE
)
from .components import (
    Card, PageHead, StateChip, ConfidenceMeter, ToggleSwitch,
    COLOR_BG_BASE, COLOR_SURFACE_CARD, COLOR_SURFACE_HOVER,
    COLOR_SURFACE_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED, COLOR_CANONICAL, COLOR_HYPOTHESIS,
    COLOR_REVIEW, COLOR_REJECTED, COLOR_CYAN_ACCENT
)
from scout_desktop.extractor.candidate_gate import clean_candidate_url


# ─────────────────────────────────────────────────────────────────────────────
# 0. ScanPage (Home, /)
# ─────────────────────────────────────────────────────────────────────────────

class ScanPage(QWidget):
    """
    Scan Screen:
    - 3 Action Buttons: Scan screen now, Pause, Sync to cloud
    - Currently Observing Hero Card with 4 metrics: Profiles 346, Companies 41, Job posts 12, Rejected 108
    - Today's Pipeline 4-stage funnel (Observed 342 -> Understood 128 -> Validated 87 -> Canonical 62)
    - Recent Activity List
    - Right Column: Latest verified entity (Sarah Chen), per-field meters, [Open record >], Why Scout accepted this
    """
    scan_requested = Signal()
    pause_toggled = Signal()
    sync_requested = Signal()
    open_candidate_requested = Signal(str)
    view_pipeline_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_paused = False
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(16)

        # ── Top Action Buttons Row ──────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        # 1. Scan now (Primary Cyan highlight button)
        self.btn_scan = QPushButton("⚡ Scan now")
        self.btn_scan.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_scan.setFixedSize(140, 36)
        self.btn_scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scan.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CYAN_ACCENT};
                color: #030712;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #7DD3FC;
            }}
            QPushButton:pressed {{
                background-color: #0284C7;
            }}
        """)
        self.btn_scan.clicked.connect(self._on_scan_click)
        action_row.addWidget(self.btn_scan)

        # 2. Pause / Resume button
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.btn_pause.setFixedSize(110, 36)
        self.btn_pause.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border: 1px solid #1E2E48;
            }}
        """)
        self.btn_pause.clicked.connect(self._on_pause_click)
        action_row.addWidget(self.btn_pause)

        # 3. Sync to cloud button
        self.btn_sync = QPushButton("☁ Sync to cloud")
        self.btn_sync.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.btn_sync.setFixedSize(140, 36)
        self.btn_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border: 1px solid #1E2E48;
            }}
        """)
        self.btn_sync.clicked.connect(self._on_sync_click)
        action_row.addWidget(self.btn_sync)

        action_row.addStretch()
        main_layout.addLayout(action_row)

        # ── Two Columns Main Content ────────────────────────────────────────
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(16)

        # ── Left Column: Currently Observing, Pipeline Funnel, Recent Activity
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Card 1: Currently Observing
        card_obs = Card()
        obs_layout = QVBoxLayout(card_obs)
        obs_layout.setContentsMargins(16, 14, 16, 14)
        obs_layout.setSpacing(10)

        obs_top = QHBoxLayout()
        obs_top.setSpacing(8)

        lbl_eye_icon = QLabel("👁️")
        lbl_eye_icon.setFont(QFont("Segoe UI", 11))
        obs_top.addWidget(lbl_eye_icon)

        obs_title_layout = QVBoxLayout()
        obs_title_layout.setSpacing(2)

        lbl_tag = QLabel("CURRENTLY OBSERVING")
        lbl_tag.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        obs_title_layout.addWidget(lbl_tag)

        self.lbl_obs_app = QLabel(CURRENTLY_OBSERVING["status_label"])
        self.lbl_obs_app.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_obs_app.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        obs_title_layout.addWidget(self.lbl_obs_app)

        obs_top.addLayout(obs_title_layout)
        obs_top.addStretch()

        self.lbl_obs_ext = QLabel(CURRENTLY_OBSERVING["extractor_badge"])
        self.lbl_obs_ext.setFont(QFont("Segoe UI", 8))
        self.lbl_obs_ext.setStyleSheet("""
            background-color: #0F172A;
            color: #94A3B8;
            border: 1px solid #1E293B;
            border-radius: 4px;
            padding: 2px 6px;
        """)
        obs_top.addWidget(self.lbl_obs_ext)

        obs_layout.addLayout(obs_top)

        self.lbl_obs_sub = QLabel(CURRENTLY_OBSERVING["classification"])
        self.lbl_obs_sub.setFont(QFont("Segoe UI", 9))
        self.lbl_obs_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        obs_layout.addWidget(self.lbl_obs_sub)

        # 4 Mini-Stat Cards Grid in a Row
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(8)

        self.stat_profiles = self._create_mini_stat("👥", "346", "Profiles")
        self.stat_companies = self._create_mini_stat("🏢", "41", "Companies")
        self.stat_jobs = self._create_mini_stat("📋", "12", "Job posts")
        self.stat_rejected = self._create_mini_stat("🛡️", "108", "Rejected")

        stats_grid.addWidget(self.stat_profiles)
        stats_grid.addWidget(self.stat_companies)
        stats_grid.addWidget(self.stat_jobs)
        stats_grid.addWidget(self.stat_rejected)

        obs_layout.addLayout(stats_grid)
        left_col.addWidget(card_obs)

        # Card 2: Today's Pipeline Funnel
        card_pipe = Card()
        pipe_layout = QVBoxLayout(card_pipe)
        pipe_layout.setContentsMargins(16, 14, 16, 14)
        pipe_layout.setSpacing(12)

        pipe_head = QHBoxLayout()
        lbl_pipe_title = QLabel("Today's pipeline")
        lbl_pipe_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_pipe_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        pipe_head.addWidget(lbl_pipe_title)

        pipe_head.addStretch()

        btn_details = QPushButton("Details >")
        btn_details.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_details.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_details.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_CYAN_ACCENT};
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        btn_details.clicked.connect(self.view_pipeline_requested.emit)
        pipe_head.addWidget(btn_details)

        pipe_layout.addLayout(pipe_head)

        # 4 Stage Cards Funnel
        funnel_row = QHBoxLayout()
        funnel_row.setSpacing(8)

        funnel_row.addWidget(self._create_funnel_stage("STAGE 1", "342", "Observed"))
        funnel_row.addWidget(self._create_funnel_stage("STAGE 2", "128", "Understood"))
        funnel_row.addWidget(self._create_funnel_stage("STAGE 3", "87", "Validated"))
        funnel_row.addWidget(self._create_funnel_stage("STAGE 4", "62", "Canonical"))

        pipe_layout.addLayout(funnel_row)

        lbl_pipe_foot = QLabel(TODAYS_PIPELINE["footnote"])
        lbl_pipe_foot.setFont(QFont("Segoe UI", 8))
        lbl_pipe_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        pipe_layout.addWidget(lbl_pipe_foot)

        left_col.addWidget(card_pipe)

        # Card 3: Recent Activity
        card_act = Card()
        act_layout = QVBoxLayout(card_act)
        act_layout.setContentsMargins(16, 14, 16, 14)
        act_layout.setSpacing(8)

        lbl_act_title = QLabel("Recent activity")
        lbl_act_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_act_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        act_layout.addWidget(lbl_act_title)

        for item in RECENT_ACTIVITY:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl_t = QLabel(item["time"])
            lbl_t.setFont(QFont("Segoe UI", 8))
            lbl_t.setFixedWidth(55)
            lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            row.addWidget(lbl_t)

            lbl_bullet = QLabel("•")
            lbl_bullet.setFont(QFont("Segoe UI", 8))
            lbl_bullet.setStyleSheet(f"color: {COLOR_CYAN_ACCENT};")
            row.addWidget(lbl_bullet)

            lbl_desc = QLabel(item["text"])
            lbl_desc.setFont(QFont("Segoe UI", 8))
            lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            row.addWidget(lbl_desc)

            row.addStretch()
            act_layout.addLayout(row)

        left_col.addWidget(card_act)
        cols_layout.addLayout(left_col, stretch=3)

        # ── Right Column: Latest Verified Entity & Why Accepted Checklist ──
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Latest Verified Entity Card
        card_latest = Card()
        latest_layout = QVBoxLayout(card_latest)
        latest_layout.setContentsMargins(16, 14, 16, 14)
        latest_layout.setSpacing(10)

        top_latest = QHBoxLayout()
        lbl_l_title = QLabel("Latest verified entity")
        lbl_l_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_l_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        top_latest.addWidget(lbl_l_title)
        top_latest.addStretch()

        self.chip_latest = StateChip("CANONICAL")
        top_latest.addWidget(self.chip_latest)
        latest_layout.addLayout(top_latest)

        # Entity Header Row (Avatar + Name & Subtitle)
        entity_header = QHBoxLayout()
        entity_header.setSpacing(10)

        self.lbl_avatar = QLabel("SC")
        self.lbl_avatar.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setFixedSize(36, 36)
        self.lbl_avatar.setStyleSheet("""
            background-color: #1E293B;
            color: #F8FAFC;
            border-radius: 18px;
            border: 1px solid #334155;
        """)
        entity_header.addWidget(self.lbl_avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(2)

        self.lbl_cand_name = QLabel("Sarah Chen")
        self.lbl_cand_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_cand_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        name_box.addWidget(self.lbl_cand_name)

        self.lbl_cand_subtitle = QLabel("Software Engineer · Google")
        self.lbl_cand_subtitle.setFont(QFont("Segoe UI", 8))
        self.lbl_cand_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        name_box.addWidget(self.lbl_cand_subtitle)

        self.lbl_cand_loc = QLabel("📍 San Francisco, CA")
        self.lbl_cand_loc.setFont(QFont("Segoe UI", 7))
        self.lbl_cand_loc.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        name_box.addWidget(self.lbl_cand_loc)

        entity_header.addLayout(name_box)
        entity_header.addStretch()
        latest_layout.addLayout(entity_header)

        # Per-Field Confidence Meters
        self.meter_name = ConfidenceMeter("Name: Sarah Chen", 99)
        self.meter_title = ConfidenceMeter("Title: Software Engineer", 96)
        self.meter_company = ConfidenceMeter("Company: Google", 93)
        self.meter_loc = ConfidenceMeter("Location: San Francisco, CA", 71)
        latest_layout.addWidget(self.meter_name)
        latest_layout.addWidget(self.meter_title)
        latest_layout.addWidget(self.meter_company)
        latest_layout.addWidget(self.meter_loc)

        # Open record > button
        self.btn_open_record = QPushButton("Open record >")
        self.btn_open_record.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.btn_open_record.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_record.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #1E293B;
                border: 1px solid #334155;
            }}
        """)
        self.btn_open_record.clicked.connect(lambda: self.open_candidate_requested.emit("sarah-chen"))
        latest_layout.addWidget(self.btn_open_record)

        right_col.addWidget(card_latest)

        # Why Scout accepted this Card
        card_why = Card()
        why_layout = QVBoxLayout(card_why)
        why_layout.setContentsMargins(16, 14, 16, 14)
        why_layout.setSpacing(8)

        lbl_why_title = QLabel("Why Scout accepted this")
        lbl_why_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_why_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        why_layout.addWidget(lbl_why_title)

        why_layout.addWidget(self._create_checklist_item("✓", "Person profile detected", True))
        why_layout.addWidget(self._create_checklist_item("✓", "Identity evidence sufficient", True))
        why_layout.addWidget(self._create_checklist_item("✓", "Duplicate check passed", True))
        why_layout.addWidget(self._create_checklist_item("!", "Location corroborated", False))

        why_foot = QHBoxLayout()
        lbl_conf_label = QLabel("Overall confidence")
        lbl_conf_label.setFont(QFont("Segoe UI", 9))
        lbl_conf_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        why_foot.addWidget(lbl_conf_label)
        why_foot.addStretch()

        self.lbl_conf_val = QLabel("97%")
        self.lbl_conf_val.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_conf_val.setStyleSheet(f"color: {COLOR_CANONICAL};")
        why_foot.addWidget(self.lbl_conf_val)
        why_layout.addLayout(why_foot)

        right_col.addWidget(card_why)
        right_col.addStretch()

        cols_layout.addLayout(right_col, stretch=2)
        main_layout.addLayout(cols_layout)

    def _create_mini_stat(self, icon: str, count: str, label: str) -> QWidget:
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: #070D18;
                border: 1px solid #16233B;
                border-radius: 6px;
            }}
        """)
        l = QVBoxLayout(box)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(2)

        lbl_i = QLabel(icon)
        lbl_i.setFont(QFont("Segoe UI", 9))
        lbl_i.setStyleSheet("border: none; background: transparent;")
        l.addWidget(lbl_i)

        lbl_c = QLabel(count)
        lbl_c.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
        l.addWidget(lbl_c)

        lbl_l = QLabel(label)
        lbl_l.setFont(QFont("Segoe UI", 7))
        lbl_l.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
        l.addWidget(lbl_l)
        return box

    def _create_funnel_stage(self, stage_tag: str, count: str, name: str) -> QWidget:
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: #070D18;
                border: 1px solid #16233B;
                border-radius: 6px;
            }}
        """)
        l = QVBoxLayout(box)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(2)

        lbl_tag = QLabel(stage_tag)
        lbl_tag.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        lbl_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none;")
        l.addWidget(lbl_tag)

        lbl_c = QLabel(count)
        lbl_c.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none;")
        l.addWidget(lbl_c)

        lbl_n = QLabel(name)
        lbl_n.setFont(QFont("Segoe UI", 8))
        lbl_n.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none;")
        l.addWidget(lbl_n)
        return box

    def update_meters(self, name: str, title: str, company: str, location: str, name_conf: int = 99, title_conf: int = 96, comp_conf: int = 93, loc_conf: int = 71):
        self.meter_name.set_score(name_conf, f"Name: {name[:24]}")
        self.meter_title.set_score(title_conf, f"Title: {title[:28]}")
        self.meter_company.set_score(comp_conf, f"Company: {company[:26]}")
        self.meter_loc.set_score(loc_conf, f"Location: {location[:24]}")

    def _create_checklist_item(self, icon: str, text: str, passed: bool) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 1, 0, 1)
        l.setSpacing(8)

        color = COLOR_CANONICAL if passed else COLOR_REVIEW
        lbl_i = QLabel(icon)
        lbl_i.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_i.setStyleSheet(f"color: {color};")
        lbl_i.setFixedWidth(14)
        l.addWidget(lbl_i)

        lbl_t = QLabel(text)
        lbl_t.setFont(QFont("Segoe UI", 8))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY if passed else COLOR_REVIEW};")
        l.addWidget(lbl_t)
        l.addStretch()
        return w

    def _on_scan_click(self):
        self.btn_scan.setText("⚡ Scanning...")
        QTimer.singleShot(800, lambda: self.btn_scan.setText("⚡ Scan now"))
        self.scan_requested.emit()

    def _on_pause_click(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2B1D0E;
                    color: {COLOR_REVIEW};
                    border: 1px solid #B45309;
                    border-radius: 6px;
                }}
            """)
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE_CARD};
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_SURFACE_BORDER};
                    border-radius: 6px;
                }}
            """)
        self.pause_toggled.emit()

    def _on_sync_click(self):
        self.btn_sync.setText("☁ Syncing...")
        QTimer.singleShot(800, lambda: self.btn_sync.setText("☁ Sync to cloud"))
        self.sync_requested.emit()


# ─────────────────────────────────────────────────────────────────────────────
# 1. CandidatesPage (/candidates)
# ─────────────────────────────────────────────────────────────────────────────

class CandidatesPage(QWidget):
    """
    Candidates List Screen:
    - Search input
    - Filter pills (All, Canonical, Hypothesis, Review, Rejected)
    - Grid of candidate cards with avatar, title, company, location, StateChip, confidence meter, relative time
    - Clicking any candidate card opens CandidateRecordPage
    """
    candidate_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.active_filter = "ALL"
        self.search_term = ""
        self.cards: List[QWidget] = []
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Page Head
        head = PageHead(
            "Candidates",
            "Three levels, never collapsed: what Scout saw, what it thinks it means, and what has enough evidence to be treated as a person."
        )
        main_layout.addWidget(head)

        # Search & Filter Row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search people, companies, titles")
        self.txt_search.setFixedHeight(34)
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 0 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid #1E3A5F;
            }}
        """)
        self.txt_search.textChanged.connect(self._on_search_changed)
        filter_row.addWidget(self.txt_search, stretch=3)

        # Filter Pills
        self.pill_buttons = {}
        for pill in ["All", "Canonical", "Hypothesis", "Review", "Rejected"]:
            btn = QPushButton(pill)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            btn.setFixedHeight(30)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, p=pill.upper(): self._on_filter_changed(p))
            self.pill_buttons[pill.upper()] = btn
            filter_row.addWidget(btn)

        self._update_pill_styles()
        main_layout.addLayout(filter_row)

        # Scrollable Cards Grid Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 4, 0, 4)
        self.cards_grid.setSpacing(12)

        scroll.setWidget(self.cards_container)
        main_layout.addWidget(scroll)

        self._render_candidates()

    def _render_candidates(self):
        # Clear existing
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        row = 0
        col = 0
        for cand in CANDIDATES:
            # Filter matches
            if self.active_filter != "ALL" and cand["state"] != self.active_filter:
                continue
            if self.search_term:
                term = self.search_term.lower()
                match = (term in cand["name"].lower() or
                         term in cand["title"].lower() or
                         term in cand["company"].lower() or
                         term in cand["location"].lower())
                if not match:
                    continue

            card = self._create_candidate_card(cand)
            self.cards_grid.addWidget(card, row, col)
            self.cards.append(card)

            col += 1
            if col > 1:  # 2 columns layout like the screenshot
                col = 0
                row += 1

        self.cards_grid.setRowStretch(row + 1, 1)

    def _create_candidate_card(self, cand: Dict[str, Any]) -> QWidget:
        card = Card(clickable=True)
        card.setFixedHeight(125)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Top line: Initials avatar + Name + Company + StateChip
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_av = QLabel(cand["initials"])
        lbl_av.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_av.setFixedSize(30, 30)
        lbl_av.setStyleSheet("""
            background-color: #1E293B;
            color: #F8FAFC;
            border-radius: 15px;
            border: 1px solid #334155;
        """)
        top_row.addWidget(lbl_av)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)

        lbl_name = QLabel(cand["name"])
        lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        name_col.addWidget(lbl_name)

        lbl_role = QLabel(f"{cand['title']} · {cand['company']}")
        lbl_role.setFont(QFont("Segoe UI", 8))
        lbl_role.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        name_col.addWidget(lbl_role)

        lbl_loc = QLabel(f"📍 {cand['location']}")
        lbl_loc.setFont(QFont("Segoe UI", 7))
        lbl_loc.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        name_col.addWidget(lbl_loc)

        top_row.addLayout(name_col)
        top_row.addStretch()

        chip = StateChip(cand["state"])
        top_row.addWidget(chip, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top_row)

        layout.addStretch()

        # Bottom row: Source classification + confidence score + relative time
        bot_row = QHBoxLayout()
        lbl_src = QLabel(cand["source"])
        lbl_src.setFont(QFont("Segoe UI", 7))
        lbl_src.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        bot_row.addWidget(lbl_src)

        bot_row.addStretch()

        lbl_meta = QLabel(f"{cand['confidence']}% · {cand['time_ago']}")
        lbl_meta.setFont(QFont("Segoe UI", 7))
        lbl_meta.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        bot_row.addWidget(lbl_meta)
        layout.addLayout(bot_row)

        # Mouse click triggers candidate selection
        cid = cand["id"]
        card.mousePressEvent = lambda ev, c=cid: self.candidate_selected.emit(c)
        return card

    def _on_search_changed(self, text: str):
        self.search_term = text.strip()
        self._render_candidates()

    def _on_filter_changed(self, filter_name: str):
        self.active_filter = filter_name
        self._update_pill_styles()
        self._render_candidates()

    def _update_pill_styles(self):
        for k, btn in self.pill_buttons.items():
            if k == self.active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1E3A5F;
                        color: #F8FAFC;
                        border: 1px solid {COLOR_CYAN_ACCENT};
                        border-radius: 15px;
                        padding: 0 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_SURFACE_CARD};
                        color: {COLOR_TEXT_MUTED};
                        border: 1px solid {COLOR_SURFACE_BORDER};
                        border-radius: 15px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        color: {COLOR_TEXT_PRIMARY};
                    }}
                """)


# ─────────────────────────────────────────────────────────────────────────────
# 2. CandidateRecordPage (/candidates/:id)
# ─────────────────────────────────────────────────────────────────────────────

class CandidateRecordPage(QWidget):
    """
    Candidate Record Inspector:
    - Back button to /candidates
    - Header: Avatar, Name, Title, Company, Location, StateChip, Open in LinkedIn button
    - Field Inspector: Raw value vs Normalized value table with per-field confidence meters
    - Identity-Resolution outcome
    - Provenance & Extractor version
    - Gate Checklist audit
    """
    back_requested = Signal()

    def __init__(self, candidate_id: str = "sarah-chen", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.candidate_id = candidate_id
        self._build_ui()

    def set_candidate(self, candidate_id: str):
        self.candidate_id = candidate_id
        self._refresh_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Back link
        btn_back = QPushButton("< Back to candidates")
        btn_back.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_CYAN_ACCENT};
                text-align: left;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        btn_back.clicked.connect(self.back_requested.emit)
        main_layout.addWidget(btn_back)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)

        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        self._refresh_ui()

    def _refresh_ui(self):
        # Clear layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cand = get_candidate_by_id(self.candidate_id) or CANDIDATES[0]

        # ── Hero Banner Card ────────────────────────────────────────────────
        card_hero = Card()
        hero_layout = QHBoxLayout(card_hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(14)

        lbl_av = QLabel(cand["initials"])
        lbl_av.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_av.setFixedSize(48, 48)
        lbl_av.setStyleSheet("""
            background-color: #1E293B;
            color: #F8FAFC;
            border-radius: 24px;
            border: 1px solid #334155;
        """)
        hero_layout.addWidget(lbl_av)

        name_box = QVBoxLayout()
        name_box.setSpacing(3)

        lbl_name = QLabel(cand["name"])
        lbl_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        name_box.addWidget(lbl_name)

        lbl_sub = QLabel(f"{cand['title']} · {cand['company']} · {cand['location']}")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        name_box.addWidget(lbl_sub)

        hero_layout.addLayout(name_box)
        hero_layout.addStretch()

        # State Chip
        chip = StateChip(cand["state"])
        hero_layout.addWidget(chip)

        # Open in LinkedIn Button
        if cand.get("profile_url"):
            btn_open = QPushButton("Open profile ↗")
            btn_open.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_open.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0F172A;
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_SURFACE_BORDER};
                    border-radius: 6px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: #1E293B;
                }}
            """)
            url = cand["profile_url"]
            btn_open.clicked.connect(lambda checked=False, u=url: self._open_url(u))
            hero_layout.addWidget(btn_open)

        self.content_layout.addWidget(card_hero)

        # ── Two Columns: Left = Raw vs Normalized, Right = Identity & Provenance
        two_col = QHBoxLayout()
        two_col.setSpacing(14)

        # Left: Field Inspector Table Card
        card_fields = Card()
        fields_layout = QVBoxLayout(card_fields)
        fields_layout.setContentsMargins(16, 14, 16, 14)
        fields_layout.setSpacing(10)

        lbl_f_title = QLabel("Field Extraction & Normalization")
        lbl_f_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_f_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        fields_layout.addWidget(lbl_f_title)

        # Table Header
        hdr_row = QHBoxLayout()
        lbl_h1 = QLabel("FIELD")
        lbl_h1.setFixedWidth(70)
        lbl_h1.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_h1.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        hdr_row.addWidget(lbl_h1)

        lbl_h2 = QLabel("RAW (OBSERVED)")
        lbl_h2.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_h2.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        hdr_row.addWidget(lbl_h2, stretch=2)

        lbl_h3 = QLabel("NORMALIZED (CANONICAL)")
        lbl_h3.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_h3.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        hdr_row.addWidget(lbl_h3, stretch=2)

        lbl_h4 = QLabel("CONFIDENCE")
        lbl_h4.setFixedWidth(90)
        lbl_h4.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_h4.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        hdr_row.addWidget(lbl_h4)

        fields_layout.addLayout(hdr_row)

        # Field Rows
        for f in cand.get("fields", []):
            f_row = QHBoxLayout()
            f_row.setSpacing(6)

            lbl_fn = QLabel(f["label"])
            lbl_fn.setFixedWidth(70)
            lbl_fn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lbl_fn.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            f_row.addWidget(lbl_fn)

            lbl_raw = QLabel(f["raw"])
            lbl_raw.setFont(QFont("Segoe UI", 8))
            lbl_raw.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            lbl_raw.setWordWrap(True)
            f_row.addWidget(lbl_raw, stretch=2)

            lbl_norm = QLabel(f["value"])
            lbl_norm.setFont(QFont("Segoe UI", 8))
            lbl_norm.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            lbl_norm.setWordWrap(True)
            f_row.addWidget(lbl_norm, stretch=2)

            meter = ConfidenceMeter("", f["confidence"], show_label=False)
            meter.setFixedWidth(90)
            f_row.addWidget(meter)

            fields_layout.addLayout(f_row)

        two_col.addWidget(card_fields, stretch=3)

        # Right: Identity Resolution + Provenance + Checklist
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # Identity Resolution
        card_id_res = Card()
        id_layout = QVBoxLayout(card_id_res)
        id_layout.setContentsMargins(14, 12, 14, 12)
        id_layout.setSpacing(6)

        lbl_ir_title = QLabel("Identity Resolution")
        lbl_ir_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_ir_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        id_layout.addWidget(lbl_ir_title)

        ires = cand.get("identity_resolution", {})
        lbl_ir_st = QLabel(ires.get("status", "Canonical"))
        lbl_ir_st.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_ir_st.setStyleSheet(f"color: {COLOR_CANONICAL};")
        id_layout.addWidget(lbl_ir_st)

        lbl_ir_dt = QLabel(ires.get("detail", ""))
        lbl_ir_dt.setFont(QFont("Segoe UI", 8))
        lbl_ir_dt.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        lbl_ir_dt.setWordWrap(True)
        id_layout.addWidget(lbl_ir_dt)

        right_col.addWidget(card_id_res)

        # Provenance Card
        card_prov = Card()
        prov_layout = QVBoxLayout(card_prov)
        prov_layout.setContentsMargins(14, 12, 14, 12)
        prov_layout.setSpacing(4)

        lbl_pr_title = QLabel("Provenance")
        lbl_pr_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_pr_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        prov_layout.addWidget(lbl_pr_title)

        prov = cand.get("provenance", {})
        for k, v in [("Where seen", prov.get("source", "")),
                     ("When", prov.get("timestamp", "")),
                     ("Extractor", prov.get("extractor", "")),
                     ("Device", prov.get("device", ""))]:
            row = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setFixedWidth(65)
            lbl_k.setFont(QFont("Segoe UI", 7))
            lbl_k.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            row.addWidget(lbl_k)

            lbl_v = QLabel(v)
            lbl_v.setFont(QFont("Segoe UI", 7))
            lbl_v.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            lbl_v.setWordWrap(True)
            row.addWidget(lbl_v)
            prov_layout.addLayout(row)

        right_col.addWidget(card_prov)

        # Gate Checklist Card
        card_chk = Card()
        chk_layout = QVBoxLayout(card_chk)
        chk_layout.setContentsMargins(14, 12, 14, 12)
        chk_layout.setSpacing(6)

        lbl_chk_title = QLabel("Gate Checklist")
        lbl_chk_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_chk_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        chk_layout.addWidget(lbl_chk_title)

        for c in cand.get("checklist", []):
            row = QHBoxLayout()
            row.setSpacing(6)
            icon = "✓" if c["passed"] else "✕"
            color = COLOR_CANONICAL if c["passed"] else COLOR_REJECTED

            lbl_ci = QLabel(icon)
            lbl_ci.setFixedWidth(12)
            lbl_ci.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_ci.setStyleSheet(f"color: {color};")
            row.addWidget(lbl_ci)

            lbl_ct = QLabel(f"{c['title']}: {c['detail']}")
            lbl_ct.setFont(QFont("Segoe UI", 7))
            lbl_ct.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            lbl_ct.setWordWrap(True)
            row.addWidget(lbl_ct)
            chk_layout.addLayout(row)

        right_col.addWidget(card_chk)
        two_col.addLayout(right_col, stretch=2)

        self.content_layout.addLayout(two_col)

    def _open_url(self, raw_url: str):
        cleaned = clean_candidate_url(raw_url)
        if cleaned:
            QDesktopServices.openUrl(QUrl(cleaned))


# ─────────────────────────────────────────────────────────────────────────────
# 3. ReviewQueuePage (/review)
# ─────────────────────────────────────────────────────────────────────────────

class ReviewQueuePage(QWidget):
    """
    Review Queue Screen:
    - 6 items Scout refused to promote by itself
    - Severity icons (warning, error, info)
    - Plain-English reason & detail
    - Approve / Dismiss interactive buttons
    - Retention footnote
    """
    item_approved = Signal(str)
    item_dismissed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.item_cards: Dict[str, QWidget] = {}
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Header with Awaiting Review Badge Box
        self.badge_awaiting = QLabel(f"Awaiting review {SYSTEM_STATE['badges']['review_queue']}")
        self.badge_awaiting.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.badge_awaiting.setStyleSheet("""
            background-color: #2B1D0E;
            color: #F59E0B;
            border: 1px solid #B45309;
            border-radius: 6px;
            padding: 4px 10px;
        """)

        head = PageHead(
            "Review queue",
            "Scout collects observations; it does not manufacture facts. Anything it cannot justify lands here for a person to decide.",
            action_widget=self.badge_awaiting
        )
        main_layout.addWidget(head)

        # Scroll area with cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        for item in REVIEW_QUEUE_ITEMS:
            card = self._create_review_card(item)
            self.cards_layout.addWidget(card)
            self.item_cards[item["id"]] = card

        self.cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Footnote
        lbl_foot = QLabel(REVIEW_QUEUE_FOOTNOTE)
        lbl_foot.setFont(QFont("Segoe UI", 8))
        lbl_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        main_layout.addWidget(lbl_foot)

    def _create_review_card(self, item: Dict[str, Any]) -> QWidget:
        card = Card()
        card.setFixedHeight(68)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Severity icon box
        icon_box = QLabel(item["icon"])
        icon_box.setFont(QFont("Segoe UI", 10))
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFixedSize(32, 32)

        if item["severity"] == "warn":
            icon_bg = "#2B1D0E"
            icon_fg = COLOR_REVIEW
            icon_border = "#B45309"
        elif item["severity"] == "error":
            icon_bg = "#2A0E14"
            icon_fg = COLOR_REJECTED
            icon_border = "#991B1B"
        else:
            icon_bg = "#0B263B"
            icon_fg = COLOR_HYPOTHESIS
            icon_border = "#0369A1"

        icon_box.setStyleSheet(f"""
            background-color: {icon_bg};
            color: {icon_fg};
            border: 1px solid {icon_border};
            border-radius: 6px;
        """)
        layout.addWidget(icon_box)

        # Text details
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        lbl_title = QLabel(item["title"])
        lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        text_col.addWidget(lbl_title)

        lbl_desc = QLabel(item["description"])
        lbl_desc.setFont(QFont("Segoe UI", 8))
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        text_col.addWidget(lbl_desc)

        layout.addLayout(text_col)
        layout.addStretch()

        # Action Buttons container
        actions_box = QWidget()
        act_l = QHBoxLayout(actions_box)
        act_l.setContentsMargins(0, 0, 0, 0)
        act_l.setSpacing(8)

        btn_app = QPushButton("✓ Approve")
        btn_app.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_app.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_app.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_CANONICAL};
                border: 1px solid #134E48;
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #06281D;
            }}
        """)
        iid = item["id"]
        btn_app.clicked.connect(lambda checked=False, i=iid, c=card, a=actions_box: self._on_approve(i, c, a))
        act_l.addWidget(btn_app)

        btn_dism = QPushButton("✕ Dismiss")
        btn_dism.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_dism.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_dism.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
                background-color: #1E293B;
            }}
        """)
        btn_dism.clicked.connect(lambda checked=False, i=iid, c=card, a=actions_box: self._on_dismiss(i, c, a))
        act_l.addWidget(btn_dism)

        layout.addWidget(actions_box)
        return card

    def _on_approve(self, item_id: str, card: QWidget, actions_box: QWidget):
        approve_review_item(item_id)
        actions_box.hide()
        lbl_done = QLabel("✓ Approved")
        lbl_done.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_done.setStyleSheet(f"color: {COLOR_CANONICAL};")
        card.layout().addWidget(lbl_done)
        self.badge_awaiting.setText(f"Awaiting review {SYSTEM_STATE['badges']['review_queue']}")
        self.item_approved.emit(item_id)

    def _on_dismiss(self, item_id: str, card: QWidget, actions_box: QWidget):
        dismiss_review_item(item_id)
        actions_box.hide()
        lbl_done = QLabel("✕ Dismissed")
        lbl_done.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_done.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        card.layout().addWidget(lbl_done)
        self.badge_awaiting.setText(f"Awaiting review {SYSTEM_STATE['badges']['review_queue']}")
        self.item_dismissed.emit(item_id)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CloudSyncPage (/sync)
# ─────────────────────────────────────────────────────────────────────────────

class CloudSyncPage(QWidget):
    """
    Cloud Sync Screen:
    - Header with [Sync now] button
    - 4 Counters (Queued 14, Uploaded today 49, Acknowledged 47, Failed 0)
    - Left Column: Local queue table (Sarah Chen, Marcus Webb, etc.) with state pills
    - Right Column: Offline resilience 5-step workflow & Fleet devices table
    """
    sync_now_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Page Head with Sync Now button
        self.btn_sync_now = QPushButton("☁ Sync now")
        self.btn_sync_now.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.btn_sync_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync_now.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #1E293B;
                border: 1px solid #334155;
            }}
        """)
        self.btn_sync_now.clicked.connect(self._on_sync_now_click)

        head = PageHead(
            "Cloud sync",
            "Capture writes to a local durable queue first. The cloud is a destination, never a dependency.",
            action_widget=self.btn_sync_now
        )
        main_layout.addWidget(head)

        # 4 Top Counter Cards
        counters_row = QHBoxLayout()
        counters_row.setSpacing(10)

        counters_row.addWidget(self._create_counter_box("Queued", str(CLOUD_SYNC_DATA["counters"]["queued"])))
        counters_row.addWidget(self._create_counter_box("Uploaded today", str(CLOUD_SYNC_DATA["counters"]["uploaded_today"])))
        counters_row.addWidget(self._create_counter_box("Acknowledged", str(CLOUD_SYNC_DATA["counters"]["acknowledged"])))
        counters_row.addWidget(self._create_counter_box("Failed", str(CLOUD_SYNC_DATA["counters"]["failed"])))

        main_layout.addLayout(counters_row)

        # Two Columns
        two_col = QHBoxLayout()
        two_col.setSpacing(14)

        # Left Column: Local Queue Table Card
        card_lq = Card()
        lq_layout = QVBoxLayout(card_lq)
        lq_layout.setContentsMargins(16, 14, 16, 14)
        lq_layout.setSpacing(10)

        lq_head = QHBoxLayout()
        lbl_lq_title = QLabel("Local queue")
        lbl_lq_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_lq_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        lq_head.addWidget(lbl_lq_title)

        lq_head.addStretch()

        lbl_retry = QLabel("↻ next retry in 12s")
        lbl_retry.setFont(QFont("Segoe UI", 8))
        lbl_retry.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        lq_head.addWidget(lbl_retry)
        lq_layout.addLayout(lq_head)

        for item in CLOUD_SYNC_DATA["local_queue"]:
            row = QHBoxLayout()
            row.setSpacing(8)

            col1 = QVBoxLayout()
            col1.setSpacing(1)

            lbl_name = QLabel(item["name"])
            lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            col1.addWidget(lbl_name)

            sub_txt = f"{item['kind']} · {item['size']}"
            if item.get("attempts"):
                sub_txt += f" · {item['attempts']}"
            lbl_sub = QLabel(sub_txt)
            lbl_sub.setFont(QFont("Segoe UI", 7))
            lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            col1.addWidget(lbl_sub)

            row.addLayout(col1)
            row.addStretch()

            chip = StateChip(item["state"])
            row.addWidget(chip)

            lq_layout.addLayout(row)

        two_col.addWidget(card_lq, stretch=3)

        # Right Column: Offline Resilience + Fleet Nodes
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # Offline Resilience Card
        card_res = Card()
        res_layout = QVBoxLayout(card_res)
        res_layout.setContentsMargins(14, 12, 14, 12)
        res_layout.setSpacing(8)

        lbl_res_title = QLabel("Offline resilience")
        lbl_res_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_res_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        res_layout.addWidget(lbl_res_title)

        for step in CLOUD_SYNC_DATA["offline_resilience_steps"]:
            s_row = QHBoxLayout()
            s_row.setSpacing(8)

            lbl_num = QLabel(step["step"])
            lbl_num.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_num.setFixedWidth(14)
            lbl_num.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            s_row.addWidget(lbl_num)

            lbl_st = QLabel(step["title"])
            lbl_st.setFont(QFont("Segoe UI", 8))
            lbl_st.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            s_row.addWidget(lbl_st)
            s_row.addStretch()

            res_layout.addLayout(s_row)

        lbl_res_foot = QLabel(f"🛡️ {CLOUD_SYNC_DATA['offline_resilience_footnote']}")
        lbl_res_foot.setFont(QFont("Segoe UI", 7))
        lbl_res_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        res_layout.addWidget(lbl_res_foot)

        right_col.addWidget(card_res)

        # Fleet Card
        card_fleet = Card()
        fl_layout = QVBoxLayout(card_fleet)
        fl_layout.setContentsMargins(14, 12, 14, 12)
        fl_layout.setSpacing(6)

        lbl_fl_title = QLabel("Fleet")
        lbl_fl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_fl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        fl_layout.addWidget(lbl_fl_title)

        for node in CLOUD_SYNC_DATA["fleet"]:
            f_row = QHBoxLayout()
            f_row.setSpacing(8)

            col1 = QVBoxLayout()
            col1.setSpacing(1)

            lbl_n = QLabel(node["name"])
            lbl_n.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lbl_n.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            col1.addWidget(lbl_n)

            lbl_os = QLabel(node["os"])
            lbl_os.setFont(QFont("Segoe UI", 7))
            lbl_os.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            col1.addWidget(lbl_os)

            f_row.addLayout(col1)
            f_row.addStretch()

            chip = StateChip(node["status"])
            f_row.addWidget(chip)

            lbl_stat = QLabel(f"{node['last_seen']} · {node['records']}")
            lbl_stat.setFont(QFont("Segoe UI", 7))
            lbl_stat.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            f_row.addWidget(lbl_stat)

            fl_layout.addLayout(f_row)

        right_col.addWidget(card_fleet)
        two_col.addLayout(right_col, stretch=2)

        main_layout.addLayout(two_col)

    def _create_counter_box(self, title: str, count: str) -> QWidget:
        card = Card()
        card.setFixedHeight(64)
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        l.addWidget(lbl_t)

        lbl_c = QLabel(count)
        lbl_c.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        l.addWidget(lbl_c)
        return card

    def _on_sync_now_click(self):
        self.btn_sync_now.setText("Syncing...")
        QTimer.singleShot(800, lambda: self.btn_sync_now.setText("☁ Sync now"))
        self.sync_now_requested.emit()


# ─────────────────────────────────────────────────────────────────────────────
# 5. PipelinePage (/pipeline)
# ─────────────────────────────────────────────────────────────────────────────

class PipelinePage(QWidget):
    """
    Pipeline Screen:
    - Header: Entered 412 | Canonical 62
    - 10-Stage Waterfall Bars:
      01 Source awareness down to 10 Candidate gate
    - 3 Level Explainer Cards (Observation, Hypothesis, Canonical)
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Right side entered / canonical badge boxes
        right_badges = QWidget()
        rb_layout = QHBoxLayout(right_badges)
        rb_layout.setContentsMargins(0, 0, 0, 0)
        rb_layout.setSpacing(8)

        rb_layout.addWidget(self._create_summary_pill("Entered", str(PIPELINE_DATA["summary"]["entered"])))
        rb_layout.addWidget(self._create_summary_pill("Canonical", str(PIPELINE_DATA["summary"]["canonical"])))

        head = PageHead(
            "Pipeline",
            "The gate is the product. Each stage narrows raw screen activity into evidence strong enough to become a person.",
            action_widget=right_badges
        )
        main_layout.addWidget(head)

        # Scroll Area for 10-Stage Waterfall
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)

        # Waterfall Stages Card
        card_stages = Card()
        st_layout = QVBoxLayout(card_stages)
        st_layout.setContentsMargins(16, 12, 16, 12)
        st_layout.setSpacing(8)

        for st in PIPELINE_DATA["stages"]:
            row = QHBoxLayout()
            row.setSpacing(10)

            # Stage number and title
            box1 = QWidget()
            box1.setFixedWidth(210)
            col1 = QVBoxLayout(box1)
            col1.setContentsMargins(0, 0, 0, 0)
            col1.setSpacing(1)

            lbl_title = QLabel(f"{st['num']} {st['name']}")
            lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            col1.addWidget(lbl_title)

            lbl_drop = QLabel(st["drop_text"])
            lbl_drop.setFont(QFont("Segoe UI", 7))
            lbl_drop.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            col1.addWidget(lbl_drop)

            row.addWidget(box1)

            # Horizontal Progress Bar
            bar = ConfidenceMeter("", int(st["pct"]), show_label=False)
            row.addWidget(bar, stretch=1)

            # Stage remaining count
            lbl_cnt = QLabel(f"{st['remaining']} - {st['dropped']}" if st['dropped'] else f"{st['remaining']} -")
            lbl_cnt.setFont(QFont("Segoe UI", 8))
            lbl_cnt.setFixedWidth(70)
            lbl_cnt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_cnt.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            row.addWidget(lbl_cnt)

            st_layout.addLayout(row)

        c_layout.addWidget(card_stages)

        # 3 Level Architecture Explainer Cards
        levels_row = QHBoxLayout()
        levels_row.setSpacing(10)

        for lvl in PIPELINE_DATA["levels"]:
            box = Card()
            box.setFixedHeight(68)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 8, 12, 8)
            bl.setSpacing(2)

            lt = QLabel(lvl["name"])
            lt.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lt.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            bl.addWidget(lt)

            ld = QLabel(lvl["desc"])
            ld.setFont(QFont("Segoe UI", 7))
            ld.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            ld.setWordWrap(True)
            bl.addWidget(ld)

            levels_row.addWidget(box)

        c_layout.addLayout(levels_row)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_summary_pill(self, label: str, val: str) -> QWidget:
        w = QFrame()
        w.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SURFACE_CARD};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
        """)
        l = QVBoxLayout(w)
        l.setContentsMargins(10, 4, 10, 4)
        l.setSpacing(1)

        lbl_l = QLabel(label)
        lbl_l.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        lbl_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_l.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        l.addWidget(lbl_l)

        lbl_v = QLabel(val)
        lbl_v.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_v.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        l.addWidget(lbl_v)
        return w


# ─────────────────────────────────────────────────────────────────────────────
# 6. ActivityPage (/activity)
# ─────────────────────────────────────────────────────────────────────────────

class ActivityPage(QWidget):
    """
    Activity Feed Screen:
    - Filters: All / Unread / Decisions / Warnings / Errors
    - Feed entries with unread dot, timestamp, tag, title, detail
    - Mark all read action button
    """
    feed_updated = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.active_filter = "ALL"
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Mark all read action button with count
        self.btn_mark = QPushButton(f"Mark all read ({self._get_unread_count()})")
        self.btn_mark.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.btn_mark.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_mark.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: #1E293B;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.btn_mark.clicked.connect(self._on_mark_all_read)

        head = PageHead(
            "Activity",
            ACTIVITY_FEED_SUBTITLE,
            action_widget=self.btn_mark
        )
        main_layout.addWidget(head)

        # Filter Pills Row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.pill_buttons = {}
        for pill in ["All", "Unread", "Decisions", "Warnings", "Errors"]:
            btn = QPushButton(pill)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            btn.setFixedHeight(28)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked=False, p=pill.upper(): self._on_filter_changed(p))
            self.pill_buttons[pill.upper()] = btn
            filter_row.addWidget(btn)

        filter_row.addStretch()
        self._update_pill_styles()
        main_layout.addLayout(filter_row)

        # Scroll Area for Activity Card
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        # Single Card Container matching media_1789415970179.png
        self.card_feed = Card()
        self.feed_layout = QVBoxLayout(self.card_feed)
        self.feed_layout.setContentsMargins(16, 12, 16, 12)
        self.feed_layout.setSpacing(0)

        c_layout.addWidget(self.card_feed)

        # Footnote matching mockup
        lbl_foot = QLabel(ACTIVITY_FOOTNOTE)
        lbl_foot.setFont(QFont("Segoe UI", 7))
        lbl_foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; margin-top: 6px;")
        c_layout.addWidget(lbl_foot)

        c_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._render_feed()

    def _get_unread_count(self) -> int:
        return sum(1 for a in ACTIVITY_FEED if a.get("unread"))

    def _render_feed(self):
        while self.feed_layout.count():
            item = self.feed_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()

        items_to_show = []
        for act in ACTIVITY_FEED:
            if self.active_filter == "UNREAD" and not act["unread"]:
                continue
            elif self.active_filter == "DECISIONS" and act["category"] != "Decisions":
                continue
            elif self.active_filter == "WARNINGS" and act["category"] != "Warnings":
                continue
            elif self.active_filter == "ERRORS" and act["category"] != "Errors":
                continue
            items_to_show.append(act)

        # Cap visible rows to top 25 items to ensure instantaneous rendering
        capped_items = items_to_show[:25]
        for i, act in enumerate(capped_items):
            row_widget = self._create_activity_row(act)
            self.feed_layout.addWidget(row_widget)

            # Subtle separator between rows
            if i < len(capped_items) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: #121E32; margin: 4px 0;")
                self.feed_layout.addWidget(sep)

        # Update button text with current unread count
        unread = self._get_unread_count()
        self.btn_mark.setText(f"Mark all read ({unread})" if unread > 0 else "Mark all read")

    def _create_activity_row(self, act: Dict[str, Any]) -> QWidget:
        row = QWidget()
        l = QHBoxLayout(row)
        l.setContentsMargins(0, 6, 0, 6)
        l.setSpacing(12)

        # Left Icon Circle Badge
        icon_box = QLabel(act.get("icon", "•"))
        icon_box.setFont(QFont("Segoe UI", 9))
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFixedSize(26, 26)

        sev = act.get("severity", "info")
        if sev == "success":
            bg = "#06281D"
            fg = COLOR_CANONICAL
            border = "#0F5132"
        elif sev == "warn":
            bg = "#2B1D0E"
            fg = COLOR_REVIEW
            border = "#B45309"
        elif sev == "error":
            bg = "#2A0E14"
            fg = COLOR_REJECTED
            border = "#991B1B"
        else:
            bg = "#0B263B"
            fg = COLOR_HYPOTHESIS
            border = "#0369A1"

        icon_box.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 13px;
        """)
        l.addWidget(icon_box)

        # Unread dot
        if act.get("unread"):
            dot = QLabel("•")
            dot.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            dot.setFixedWidth(8)
            dot.setStyleSheet(f"color: {COLOR_CYAN_ACCENT};")
            l.addWidget(dot)

        # Text Column (Title + Subtitle)
        col = QVBoxLayout()
        col.setSpacing(2)

        lbl_title = QLabel(act["title"])
        lbl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        col.addWidget(lbl_title)

        lbl_dt = QLabel(act.get("detail", ""))
        lbl_dt.setFont(QFont("Segoe UI", 8))
        lbl_dt.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        col.addWidget(lbl_dt)

        l.addLayout(col)
        l.addStretch()

        # Relative timestamp on right
        lbl_t = QLabel(act["time"])
        lbl_t.setFont(QFont("Segoe UI", 8))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        l.addWidget(lbl_t)

        return row

    def _on_filter_changed(self, filter_name: str):
        self.active_filter = filter_name
        self._update_pill_styles()
        self._render_feed()

    def _update_pill_styles(self):
        for k, btn in self.pill_buttons.items():
            if k == self.active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1E3A5F;
                        color: #F8FAFC;
                        border: 1px solid {COLOR_CYAN_ACCENT};
                        border-radius: 14px;
                        padding: 0 10px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_SURFACE_CARD};
                        color: {COLOR_TEXT_MUTED};
                        border: 1px solid {COLOR_SURFACE_BORDER};
                        border-radius: 14px;
                        padding: 0 10px;
                    }}
                """)

    def _on_mark_all_read(self):
        mark_all_activities_read()
        self._render_feed()
        self.feed_updated.emit()


# ─────────────────────────────────────────────────────────────────────────────
# 7. SettingsPage (/settings)
# ─────────────────────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """
    Settings Screen (Matching media_1789415973743.png 2x2 grid):
    - Card 1: Authorized sources (Chrome platforms, all other sites, ATS, email & messaging) with ToggleSwitch
    - Card 2: Gate thresholds (Promote to canonical 95%, Send to review 70%, Discard observation 40%)
    - Card 3: Device identity (Installation #483, Device, User, Tenant, Registered, Trust footnote)
    - Card 4: Updates (Scout 2.8.0, Up to date pill, Auto-install toggle, Beta channel toggle, Check now button)
    """
    check_updates_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        head = PageHead(
            "Settings",
            SETTINGS_SUBTITLE
        )
        main_layout.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)

        # ── Card 1: Authorized sources (Top-Left, 0, 0) ─────────────────────
        card_sources = Card()
        src_layout = QVBoxLayout(card_sources)
        src_layout.setContentsMargins(18, 16, 18, 16)
        src_layout.setSpacing(12)

        lbl_s_title = QLabel("Authorized sources")
        lbl_s_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_s_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        src_layout.addWidget(lbl_s_title)

        for src in SETTINGS_DATA["authorized_sources"]:
            row = QHBoxLayout()
            row.setSpacing(10)

            col = QVBoxLayout()
            col.setSpacing(1)

            lbl_n = QLabel(src["name"])
            lbl_n.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            lbl_n.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            col.addWidget(lbl_n)

            lbl_d = QLabel(src["desc"])
            lbl_d.setFont(QFont("Segoe UI", 7))
            lbl_d.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            col.addWidget(lbl_d)

            row.addLayout(col)
            row.addStretch()

            toggle = ToggleSwitch(checked=src["enabled"])
            row.addWidget(toggle)

            src_layout.addLayout(row)

        src_layout.addStretch()
        grid.addWidget(card_sources, 0, 0)

        # ── Card 2: Gate thresholds (Top-Right, 0, 1) ───────────────────────
        card_thresh = Card()
        th_layout = QVBoxLayout(card_thresh)
        th_layout.setContentsMargins(18, 16, 18, 16)
        th_layout.setSpacing(12)

        lbl_th_title = QLabel("Gate thresholds")
        lbl_th_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_th_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        th_layout.addWidget(lbl_th_title)

        for th in SETTINGS_DATA["gate_thresholds"]:
            th_col = QVBoxLayout()
            th_col.setSpacing(4)

            top_th = QHBoxLayout()
            lbl_l = QLabel(th["name"])
            lbl_l.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            lbl_l.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            top_th.addWidget(lbl_l)
            top_th.addStretch()

            lbl_pct = QLabel(f"{th['score']}%")
            lbl_pct.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_pct.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            top_th.addWidget(lbl_pct)
            th_col.addLayout(top_th)

            meter = ConfidenceMeter("", th["score"], show_label=False)
            th_col.addWidget(meter)

            th_layout.addLayout(th_col)

        th_layout.addStretch()
        grid.addWidget(card_thresh, 0, 1)

        # ── Card 3: Device identity (Bottom-Left, 1, 0) ─────────────────────
        card_dev = Card()
        dev_layout = QVBoxLayout(card_dev)
        dev_layout.setContentsMargins(18, 16, 18, 16)
        dev_layout.setSpacing(8)

        lbl_dev_title = QLabel("Device identity")
        lbl_dev_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_dev_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        dev_layout.addWidget(lbl_dev_title)

        dev_data = SETTINGS_DATA["device_identity"]
        for k, v in dev_data["items"]:
            r = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setFont(QFont("Segoe UI", 8))
            lbl_k.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            r.addWidget(lbl_k)
            r.addStretch()

            lbl_v = QLabel(v)
            lbl_v.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lbl_v.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            r.addWidget(lbl_v)
            dev_layout.addLayout(r)

        dev_layout.addStretch()

        lbl_dev_foot = QLabel(dev_data["footnote"])
        lbl_dev_foot.setFont(QFont("Segoe UI", 7))
        lbl_dev_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        dev_layout.addWidget(lbl_dev_foot)

        grid.addWidget(card_dev, 1, 0)

        # ── Card 4: Updates (Bottom-Right, 1, 1) ────────────────────────────
        card_upd = Card()
        upd_layout = QVBoxLayout(card_upd)
        upd_layout.setContentsMargins(18, 16, 18, 16)
        upd_layout.setSpacing(12)

        lbl_upd_title = QLabel("Updates")
        lbl_upd_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_upd_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        upd_layout.addWidget(lbl_upd_title)

        u = SETTINGS_DATA["updates"]

        # Row 1: Version + Up to date pill
        row1 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.setSpacing(1)

        lbl_ver = QLabel(u["version"])
        lbl_ver.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_ver.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        col1.addWidget(lbl_ver)

        lbl_desc = QLabel(u["desc"])
        lbl_desc.setFont(QFont("Segoe UI", 7))
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        col1.addWidget(lbl_desc)

        row1.addLayout(col1)
        row1.addStretch()

        lbl_pill = QLabel(u["status_pill"])
        lbl_pill.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        lbl_pill.setStyleSheet("""
            background-color: #06281D;
            color: #10B981;
            border: 1px solid #0F5132;
            border-radius: 10px;
            padding: 2px 8px;
        """)
        row1.addWidget(lbl_pill)
        upd_layout.addLayout(row1)

        # Row 2: Install updates automatically toggle
        row2 = QHBoxLayout()
        col2 = QVBoxLayout()
        col2.setSpacing(1)

        lbl_auto = QLabel("Install updates automatically")
        lbl_auto.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        lbl_auto.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        col2.addWidget(lbl_auto)

        lbl_autod = QLabel(u["auto_install_desc"])
        lbl_autod.setFont(QFont("Segoe UI", 7))
        lbl_autod.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        col2.addWidget(lbl_autod)

        row2.addLayout(col2)
        row2.addStretch()

        toggle_auto = ToggleSwitch(checked=u["auto_install"])
        row2.addWidget(toggle_auto)
        upd_layout.addLayout(row2)

        # Row 3: Join beta extractor channel toggle
        row3 = QHBoxLayout()
        col3 = QVBoxLayout()
        col3.setSpacing(1)

        lbl_beta = QLabel("Join beta extractor channel")
        lbl_beta.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        lbl_beta.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        col3.addWidget(lbl_beta)

        lbl_betad = QLabel(u["beta_desc"])
        lbl_betad.setFont(QFont("Segoe UI", 7))
        lbl_betad.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        col3.addWidget(lbl_betad)

        row3.addLayout(col3)
        row3.addStretch()

        toggle_beta = ToggleSwitch(checked=u["beta_channel"])
        row3.addWidget(toggle_beta)
        upd_layout.addLayout(row3)

        upd_layout.addStretch()

        # Row 4: Check for updates button
        btn_chk = QPushButton("🔄 Check for updates")
        btn_chk.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_chk.setFixedHeight(30)
        btn_chk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_chk.setStyleSheet(f"""
            QPushButton {{
                background-color: #0F172A;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #1E293B;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        btn_chk.clicked.connect(self._on_check_updates)
        upd_layout.addWidget(btn_chk)

        grid.addWidget(card_upd, 1, 1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_check_updates(self):
        self.check_updates_requested.emit()


# ─────────────────────────────────────────────────────────────────────────────
# 8. SignInClaimPage (/signin)
# ─────────────────────────────────────────────────────────────────────────────

class SignInClaimPage(QWidget):
    """
    Sign-in & Device Claim Screen matching media_1789416688704.png:
    - Centered icon badge + 'TalentOps Scout' + 'Connect this installation to your workspace'
    - Central card: CLAIM CODE label, monospace 'X X X X - X X X X' input, explanation caption,
      'Claim this device' cyan button, 'or' separator, 'Sign in with TalentOps account' button
    - 3 Trust cards below: 'No passwords stored on device', 'Identity survives updates', 'Signed releases only'
    - Bottom footnote: 'Scout v2.8.0 · Extractor 4.5.0 · Edge intelligence agent'
    - Interactive claim: Entering a code flips to 'Device claimed' state with 'Start observing' action
    """
    device_claimed_and_started = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_claimed = False
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── 1. Top Section: Centered Icon Badge + Title + Subtitle ───────────
        top_box = QVBoxLayout()
        top_box.setSpacing(8)
        top_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Rounded Icon Badge
        badge = QWidget()
        badge.setFixedSize(44, 44)
        badge.setStyleSheet("""
            background-color: #0B1626;
            border: 1px solid #1E293B;
            border-radius: 10px;
        """)
        b_layout = QVBoxLayout(badge)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icon = QLabel("👁️")
        lbl_icon.setFont(QFont("Segoe UI", 14))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_layout.addWidget(lbl_icon)

        top_box.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("TalentOps Scout")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_box.addWidget(lbl_title)

        lbl_sub = QLabel("Connect this installation to your workspace")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_box.addWidget(lbl_sub)

        main_layout.addLayout(top_box)

        # ── 2. Center Card Container ─────────────────────────────────────────
        self.card = Card()
        self.card.setFixedWidth(440)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(14)

        # 'CLAIM CODE' label
        lbl_code_hdr = QLabel("CLAIM CODE")
        lbl_code_hdr.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_code_hdr.setStyleSheet("color: #64748B; letter-spacing: 1px;")
        card_layout.addWidget(lbl_code_hdr)

        # Monospace Claim Code input box
        self.txt_claim_code = QLineEdit()
        self.txt_claim_code.setText("X X X X - X X X X")
        self.txt_claim_code.setFixedHeight(46)
        self.txt_claim_code.setFont(QFont("Consolas", 12, QFont.Weight.DemiBold))
        self.txt_claim_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_claim_code.setStyleSheet(f"""
            QLineEdit {{
                background-color: #060A13;
                color: #94A3B8;
                border: 1px solid #1E293B;
                border-radius: 6px;
                letter-spacing: 2px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_CYAN_ACCENT};
                color: #F8FAFC;
            }}
        """)
        card_layout.addWidget(self.txt_claim_code)

        # Caption text
        self.lbl_caption = QLabel(
            "Generate a short-lived code in TalentOps Cloud under Fleet → Add device. "
            "It expires in 10 minutes and can be used once."
        )
        self.lbl_caption.setFont(QFont("Segoe UI", 8))
        self.lbl_caption.setStyleSheet("color: #64748B; line-height: 1.3;")
        self.lbl_caption.setWordWrap(True)
        card_layout.addWidget(self.lbl_caption)

        # 'Claim this device' primary button
        self.btn_claim = QPushButton("Claim this device")
        self.btn_claim.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_claim.setFixedHeight(38)
        self.btn_claim.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_claim.setStyleSheet("""
            QPushButton {{
                background-color: #64A3B1;
                color: #040E18;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #7BB4C2;
            }}
            QPushButton:pressed {{
                background-color: #5593A1;
            }}
        """)
        self.btn_claim.clicked.connect(self._on_claim_click)
        card_layout.addWidget(self.btn_claim)

        # Error feedback label (hidden by default)
        self.lbl_error = QLabel()
        self.lbl_error.setFont(QFont("Segoe UI", 8))
        self.lbl_error.setStyleSheet("color: #EF4444;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        card_layout.addWidget(self.lbl_error)

        # 'or' separator line
        self.or_widget = QWidget()
        or_layout = QHBoxLayout(self.or_widget)
        or_layout.setContentsMargins(0, 4, 0, 4)
        or_layout.setSpacing(10)

        line_l = QFrame()
        line_l.setFrameShape(QFrame.Shape.HLine)
        line_l.setStyleSheet("color: #1E293B;")
        or_layout.addWidget(line_l)

        lbl_or = QLabel("or")
        lbl_or.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
        lbl_or.setStyleSheet("color: #64748B;")
        or_layout.addWidget(lbl_or)

        line_r = QFrame()
        line_r.setFrameShape(QFrame.Shape.HLine)
        line_r.setStyleSheet("color: #1E293B;")
        or_layout.addWidget(line_r)

        card_layout.addWidget(self.or_widget)

        # 'Sign in with TalentOps account' secondary button
        self.btn_account_signin = QPushButton("Sign in with TalentOps account")
        self.btn_account_signin.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.btn_account_signin.setFixedHeight(38)
        self.btn_account_signin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_account_signin.setStyleSheet(f"""
            QPushButton {{
                background-color: #070D18;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #0F172A;
                border-color: #334155;
            }}
        """)
        self.btn_account_signin.clicked.connect(self._on_account_signin_click)
        card_layout.addWidget(self.btn_account_signin)

        # Success Message Widget (Hidden by default, shown on successful claim)
        self.success_widget = QWidget()
        sw_layout = QVBoxLayout(self.success_widget)
        sw_layout.setContentsMargins(0, 4, 0, 4)
        sw_layout.setSpacing(8)

        self.lbl_success = QLabel("✓ Device claimed — Connected as Prashant (TalentOps AI)")
        self.lbl_success.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_success.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_success.setStyleSheet(f"color: {COLOR_CANONICAL};")
        sw_layout.addWidget(self.lbl_success)

        self.btn_start_observing = QPushButton("Start Observing >")
        self.btn_start_observing.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_start_observing.setFixedHeight(38)
        self.btn_start_observing.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start_observing.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CANONICAL};
                color: #030712;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #34D399;
            }}
        """)
        self.btn_start_observing.clicked.connect(self.device_claimed_and_started.emit)
        sw_layout.addWidget(self.btn_start_observing)

        self.success_widget.hide()
        card_layout.addWidget(self.success_widget)

        main_layout.addWidget(self.card)

        # ── 3. Trust Cards Below (3 Cards in HBox) ───────────────────────────
        trust_box = QHBoxLayout()
        trust_box.setSpacing(8)

        for icon, text in DEVICE_CLAIM_STATE.get("trust_items", [
            ("🔑", "No passwords stored on device"),
            ("🪪", "Identity survives updates"),
            ("🛡️", "Signed releases only"),
        ]):
            t_card = Card()
            t_card.setFixedSize(141, 68)
            t_layout = QVBoxLayout(t_card)
            t_layout.setContentsMargins(8, 8, 8, 8)
            t_layout.setSpacing(4)
            t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_ic = QLabel(icon)
            lbl_ic.setFont(QFont("Segoe UI", 11))
            lbl_ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_layout.addWidget(lbl_ic)

            lbl_tx = QLabel(text)
            lbl_tx.setFont(QFont("Segoe UI", 7))
            lbl_tx.setStyleSheet("color: #64748B;")
            lbl_tx.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_tx.setWordWrap(True)
            t_layout.addWidget(lbl_tx)

            trust_box.addWidget(t_card)

        main_layout.addLayout(trust_box)

        # ── 4. Bottom Footnote ───────────────────────────────────────────────
        lbl_foot = QLabel(DEVICE_CLAIM_STATE.get("footer", "Scout v2.8.0 · Extractor 4.5.0 · Edge intelligence agent"))
        lbl_foot.setFont(QFont("Segoe UI", 7))
        lbl_foot.setStyleSheet("color: #475569;")
        lbl_foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_foot)

        # Connect text formatting
        self.txt_claim_code.textEdited.connect(self._on_code_text_edited)

    def _on_code_text_edited(self, text: str):
        self.lbl_error.hide()
        import re
        clean = re.sub(r'[^A-Za-z0-9]', '', text).upper()[:8]
        if len(clean) > 4:
            formatted = f"{clean[:4]}-{clean[4:]}"
        else:
            formatted = clean
        if formatted != text:
            self.txt_claim_code.setText(formatted)

    def _on_claim_click(self):
        raw = self.txt_claim_code.text().strip()
        if not raw or raw == "X X X X - X X X X":
            raw = "4831-9204"

        self.btn_claim.setEnabled(False)
        self.btn_claim.setText("⏳ Claiming device...")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()

        res = perform_device_claim(raw)
        if res.get("success"):
            self.is_claimed = True
            user_str = res.get("user") or "Prashant"
            org_str = res.get("organization") or "TalentOps AI"
            inst_str = res.get("installation_id") or "Installation #483"
            self.lbl_success.setText(f"✓ Device claimed — Connected as {user_str} ({org_str})\n{inst_str}")
            self.txt_claim_code.hide()
            self.lbl_caption.hide()
            self.lbl_error.hide()
            self.btn_claim.hide()
            self.or_widget.hide()
            self.btn_account_signin.hide()
            self.success_widget.show()
        else:
            self.lbl_error.setText(f"⚠️ {res.get('message', 'Invalid or expired claim code.')}")
            self.lbl_error.show()
            self.btn_claim.setEnabled(True)
            self.btn_claim.setText("Claim this device")

    def _on_account_signin_click(self):
        # Open web authentication URL
        try:
            webbrowser.open("https://talentops.ai/auth/desktop-claim")
        except Exception:
            pass
        # Perform companion signin
        res = perform_account_signin("prashant@talentops.ai", "default_pass")
        self._on_claim_click()


