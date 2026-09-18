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
from PySide6.QtGui import QFont, QColor, QCursor, QDesktopServices, QPainter

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
    COLOR_BG_BASE, COLOR_RAIL, COLOR_SURFACE, COLOR_SURFACE_CARD, COLOR_SURFACE_HOVER,
    COLOR_SURFACE_ACTIVE, COLOR_SURFACE_BORDER, COLOR_SURFACE_BORDER_LIGHT,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    COLOR_CANONICAL, COLOR_HYPOTHESIS, COLOR_REVIEW, COLOR_REJECTED,
    COLOR_CYAN_ACCENT, COLOR_PRIMARY, COLOR_ON_PRIMARY
)
from scout_desktop.version import __version__, EXTRACTOR_VERSION
from scout_desktop.extractor.candidate_gate import clean_candidate_url


def _smart_truncate(prefix: str, text: Optional[str], max_len: int = 34) -> str:
    """Safely formats meter labels without slicing words in half (e.g. avoiding 'Professio')."""
    if not text:
        return f"{prefix}: —"
    val = text.strip()
    if not val or val == "—":
        return f"{prefix}: —"
    full = f"{prefix}: {val}"
    if len(full) <= max_len:
        return full
    budget = max_len - len(prefix) - 5  # space for prefix + ": " + "..."
    if budget < 5:
        budget = 8
    truncated = val[:budget]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{prefix}: {truncated}..."


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
        self._current_candidate_id: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # ── 1. Top Command Console & Live Telemetry Header (Card) ──────────
        head_card = Card()
        head_layout = QVBoxLayout(head_card)
        head_layout.setContentsMargins(18, 14, 18, 14)
        head_layout.setSpacing(12)

        # Header Row: Telemetry pill & Action Matrix
        top_h_row = QHBoxLayout()
        top_h_row.setSpacing(8)

        dot_telemetry = QLabel("■")
        dot_telemetry.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        dot_telemetry.setStyleSheet("color: #FFFFFF;")
        top_h_row.addWidget(dot_telemetry)

        lbl_sys_eng = QLabel("SYS.ENGINE // CONTINUOUS TELEMETRY")
        lbl_sys_eng.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_sys_eng.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        top_h_row.addWidget(lbl_sys_eng)

        lbl_uptime_pill = QLabel("99.8% UP • 01:39:38")
        lbl_uptime_pill.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_uptime_pill.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 4px;
            padding: 2px 7px;
        """)
        top_h_row.addWidget(lbl_uptime_pill)
        top_h_row.addStretch()

        # Action Buttons matching Stitch design: Solid white Scan, Dark outline Pause & Sync
        self.btn_scan = QPushButton("▶ Scan now")
        self.btn_scan.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_scan.setFixedHeight(32)
        self.btn_scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scan.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: #0E0E0E;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #E2E2E2;
            }}
            QPushButton:pressed {{
                background-color: #C6C6C7;
            }}
        """)
        self.btn_scan.clicked.connect(self._on_scan_click)
        top_h_row.addWidget(self.btn_scan)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        self.btn_pause.setFixedHeight(32)
        self.btn_pause.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_pause.clicked.connect(self._on_pause_click)
        top_h_row.addWidget(self.btn_pause)

        self.btn_sync = QPushButton("↻ Sync")
        self.btn_sync.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        self.btn_sync.setFixedHeight(32)
        self.btn_sync.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_sync.clicked.connect(self._on_sync_click)
        top_h_row.addWidget(self.btn_sync)

        head_layout.addLayout(top_h_row)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Scout is working for you")
        lbl_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        title_box.addWidget(lbl_title)

        lbl_desc = QLabel("Watching authorized sources only. Auto-ingestion requires a stable profile or verified contact; ambiguous captures go to review.")
        lbl_desc.setFont(QFont("Segoe UI", 8))
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        title_box.addWidget(lbl_desc)
        head_layout.addLayout(title_box)

        # Current Observation Ribbon
        obs_ribbon = QFrame()
        obs_ribbon.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_BASE};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        obs_r_layout = QHBoxLayout(obs_ribbon)
        obs_r_layout.setContentsMargins(12, 6, 12, 6)
        obs_r_layout.setSpacing(8)

        dot_obs = QLabel("■")
        dot_obs.setFont(QFont("Consolas", 7))
        dot_obs.setStyleSheet("color: #FFFFFF;")
        obs_r_layout.addWidget(dot_obs)

        lbl_obs_tag = QLabel("CURRENTLY OBSERVING:")
        lbl_obs_tag.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_obs_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        obs_r_layout.addWidget(lbl_obs_tag)

        self.lbl_obs_app = QLabel("antigravity.exe • unauthorized")
        self.lbl_obs_app.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.lbl_obs_app.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        obs_r_layout.addWidget(self.lbl_obs_app)

        self.lbl_obs_ext = QLabel("ext-4.5.2")
        self.lbl_obs_ext.setFont(QFont("Consolas", 7))
        self.lbl_obs_ext.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_MUTED};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 5px;
        """)
        obs_r_layout.addWidget(self.lbl_obs_ext)

        obs_r_layout.addStretch()

        self.lbl_gate = QLabel("IDENTITY GATE v2.8.3: ANCHOR REQUIRED")
        self.lbl_gate.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_gate.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        obs_r_layout.addWidget(self.lbl_gate)
        self.lbl_obs_sub = self.lbl_gate  # Compatibility alias for app.py

        self.lbl_conf = QLabel("CONF: 0.97")
        self.lbl_conf.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_conf.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        obs_r_layout.addWidget(self.lbl_conf)

        head_layout.addWidget(obs_ribbon)

        # Edge Process Load & Telemetry HUD Ribbon
        self.load_ribbon = QFrame()
        self.load_ribbon.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_BASE};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        load_r_layout = QHBoxLayout(self.load_ribbon)
        load_r_layout.setContentsMargins(12, 6, 12, 6)
        load_r_layout.setSpacing(10)

        self.lbl_load_dot = QLabel("●")
        self.lbl_load_dot.setFont(QFont("Consolas", 7))
        self.lbl_load_dot.setStyleSheet("color: #10B981;")
        load_r_layout.addWidget(self.lbl_load_dot)

        lbl_load_tag = QLabel("EDGE PROCESS LOAD:")
        lbl_load_tag.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_load_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        load_r_layout.addWidget(lbl_load_tag)

        self.lbl_hud_load_pill = QLabel("OPTIMAL")
        self.lbl_hud_load_pill.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_hud_load_pill.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_load_pill)

        self.lbl_hud_cpu = QLabel("CPU: 0.0%")
        self.lbl_hud_cpu.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_hud_cpu.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_cpu)

        self.lbl_hud_ram = QLabel("RAM: 0.0 MB")
        self.lbl_hud_ram.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_hud_ram.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_ram)

        load_r_layout.addStretch()

        self.lbl_hud_latency = QLabel("LATENCY: 0.4ms")
        self.lbl_hud_latency.setFont(QFont("Consolas", 7))
        self.lbl_hud_latency.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_MUTED};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_latency)

        self.lbl_hud_queue = QLabel("QUEUE: 0 PENDING")
        self.lbl_hud_queue.setFont(QFont("Consolas", 7))
        self.lbl_hud_queue.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_MUTED};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_queue)

        self.lbl_hud_state = QLabel("ENGINE: STEADY")
        self.lbl_hud_state.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_hud_state.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_CARD};
            color: {COLOR_TEXT_SECONDARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        load_r_layout.addWidget(self.lbl_hud_state)

        head_layout.addWidget(self.load_ribbon)
        main_layout.addWidget(head_card)

        # ── 2. Two Columns Main Content ─────────────────────────────────────
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(14)

        # ── Left Column: Metrics Grid, Pipeline Intake, Edge Audit Log (7 cols)
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        # 4 Mini-Stat Cards Grid in a Row
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(10)

        self.stat_profiles = self._create_monochrome_stat("PROFILES", "346", "+18% VS LAST TICK")
        self.stat_companies = self._create_monochrome_stat("COMPANIES", "41", "UNIQUE DOMAINS")
        self.stat_jobs = self._create_monochrome_stat("JOB POSTS", "12", "MATCHED REQS")
        self.stat_rejected = self._create_monochrome_stat("REJECTED", "108", "NO SYNTH RES")

        stats_grid.addWidget(self.stat_profiles)
        stats_grid.addWidget(self.stat_companies)
        stats_grid.addWidget(self.stat_jobs)
        stats_grid.addWidget(self.stat_rejected)
        left_col.addLayout(stats_grid)

        # Pipeline Intake & Gating Card
        card_pipe = Card()
        pipe_layout = QVBoxLayout(card_pipe)
        pipe_layout.setContentsMargins(16, 12, 16, 12)
        pipe_layout.setSpacing(10)

        pipe_head = QHBoxLayout()
        lbl_pipe_title = QLabel("PIPELINE INTAKE & GATING")
        lbl_pipe_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_pipe_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; letter-spacing: 0.5px;")
        pipe_head.addWidget(lbl_pipe_title)

        pipe_head.addStretch()

        lbl_stages_tag = QLabel("STAGES 01—04")
        lbl_stages_tag.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_stages_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        pipe_head.addWidget(lbl_stages_tag)

        btn_details = QPushButton("Details >")
        btn_details.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        btn_details.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_details.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_PRIMARY};
                text-decoration: underline;
                padding-left: 6px;
            }}
        """)
        btn_details.clicked.connect(self.view_pipeline_requested.emit)
        pipe_head.addWidget(btn_details)
        pipe_layout.addLayout(pipe_head)

        # 4 Funnel Stages with Monochromatic Progress Bars
        stages = [
            ("STAGE 01: OBSERVED", "342", "100.0%", 1.00),
            ("STAGE 02: UNDERSTOOD", "128", "37.4%", 0.374),
            ("STAGE 03: VALIDATED", "87", "25.4%", 0.254),
            ("STAGE 04: CANONICAL", "62", "18.1%", 0.181)
        ]

        for st_name, st_val, st_pct_str, st_pct_val in stages:
            st_box = QVBoxLayout()
            st_box.setSpacing(2)

            st_row = QHBoxLayout()
            lbl_sn = QLabel(st_name)
            lbl_sn.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            lbl_sn.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY if 'CANONICAL' in st_name or 'OBSERVED' in st_name else COLOR_TEXT_SECONDARY};")
            st_row.addWidget(lbl_sn)

            st_row.addStretch()

            lbl_sv = QLabel(st_val)
            lbl_sv.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            lbl_sv.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            st_row.addWidget(lbl_sv)

            lbl_sp = QLabel(st_pct_str)
            lbl_sp.setFont(QFont("Consolas", 7))
            lbl_sp.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            st_row.addWidget(lbl_sp)
            st_box.addLayout(st_row)

            bar = _MiniProgressBarWidget(st_pct_val)
            st_box.addWidget(bar)
            pipe_layout.addLayout(st_box)

        # Burndown Velocity Strip
        burn_row = QHBoxLayout()
        burn_row.setContentsMargins(0, 4, 0, 0)
        lbl_bv = QLabel("BURNDOWN VELOCITY")
        lbl_bv.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_bv.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        burn_row.addWidget(lbl_bv)

        burn_row.addStretch()

        spark = _MiniSparklineWidget()
        spark.setFixedWidth(80)
        burn_row.addWidget(spark)

        lbl_rate = QLabel("+4.2/SEC")
        lbl_rate.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_rate.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        burn_row.addWidget(lbl_rate)
        pipe_layout.addLayout(burn_row)

        left_col.addWidget(card_pipe)

        # Edge Audit Log Card
        card_act = Card()
        act_layout = QVBoxLayout(card_act)
        act_layout.setContentsMargins(16, 12, 16, 12)
        act_layout.setSpacing(8)

        act_head = QHBoxLayout()
        lbl_act_title = QLabel("EDGE AUDIT LOG")
        lbl_act_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_act_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; letter-spacing: 0.5px;")
        act_head.addWidget(lbl_act_title)

        act_head.addStretch()

        lbl_act_stream = QLabel("STREAM: LIVE")
        lbl_act_stream.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_act_stream.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        act_head.addWidget(lbl_act_stream)
        act_layout.addLayout(act_head)

        log_entries = [
            ("■", "14:02:11.890", "PARSED: Danielle Mason", "GATE: PASSED [ID#9901]", True),
            ("■", "14:01:54.204", "INDEXED: Moyo Systems Corp", "RESOLVED_DOMAIN", True),
            ("□", "14:00:32.112", "DROP: duplicate_collision_uuid_84", "[REJECTED]", False),
            ("■", "13:58:09.671", "AUTH_REVOKE: session_ping_ack", "SYNC_FLUSH", True)
        ]

        for dot_char, time_str, desc_str, badge_str, is_primary in log_entries:
            row_f = QFrame()
            row_f.setFixedHeight(28)
            row_f.setStyleSheet("background: transparent; border-bottom: 1px solid #1F1F1F;")
            r_l = QHBoxLayout(row_f)
            r_l.setContentsMargins(0, 2, 0, 2)
            r_l.setSpacing(8)

            lbl_d = QLabel(dot_char)
            lbl_d.setFont(QFont("Consolas", 7))
            lbl_d.setStyleSheet("color: #FFFFFF;" if is_primary else f"color: {COLOR_TEXT_MUTED};")
            r_l.addWidget(lbl_d)

            lbl_t = QLabel(time_str)
            lbl_t.setFont(QFont("Consolas", 7))
            lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            r_l.addWidget(lbl_t)

            lbl_m = QLabel(desc_str)
            lbl_m.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold if is_primary else QFont.Weight.Normal))
            lbl_m.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY if is_primary else COLOR_TEXT_MUTED};")
            r_l.addWidget(lbl_m)

            r_l.addStretch()

            lbl_b = QLabel(badge_str)
            lbl_b.setFont(QFont("Consolas", 7))
            lbl_b.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            r_l.addWidget(lbl_b)

            act_layout.addWidget(row_f)

        left_col.addWidget(card_act)
        cols_layout.addLayout(left_col, stretch=7)

        # ── Right Column: Latest Verified Entity & Storage Daemon (5 cols)
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # Latest Verified Entity Card
        card_latest = Card()
        latest_layout = QVBoxLayout(card_latest)
        latest_layout.setContentsMargins(16, 14, 16, 14)
        latest_layout.setSpacing(10)

        top_latest = QHBoxLayout()
        lbl_l_title = QLabel("LATEST VERIFIED ENTITY")
        lbl_l_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_l_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; letter-spacing: 0.5px;")
        top_latest.addWidget(lbl_l_title)
        top_latest.addStretch()

        self.chip_latest = StateChip("CANONICAL")
        top_latest.addWidget(self.chip_latest)
        latest_layout.addLayout(top_latest)

        # Entity Identity Block
        entity_header = QHBoxLayout()
        entity_header.setSpacing(10)

        self.lbl_avatar = QLabel("DM")
        self.lbl_avatar.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_avatar.setFixedSize(44, 44)
        self.lbl_avatar.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: #FFFFFF;
            border-radius: 6px;
            border: 1px solid {COLOR_SURFACE_BORDER};
        """)
        entity_header.addWidget(self.lbl_avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(1)

        name_row = QHBoxLayout()
        self.lbl_cand_name = QLabel("Danielle Mason")
        self.lbl_cand_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_cand_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; background: transparent; border: none;")
        name_row.addWidget(self.lbl_cand_name)

        chk = QLabel("✓")
        chk.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        chk.setStyleSheet("color: #FFFFFF;")
        name_row.addWidget(chk)
        name_row.addStretch()
        name_box.addLayout(name_row)

        self.lbl_cand_subtitle = QLabel("People Operations Specialist • Moyo")
        self.lbl_cand_subtitle.setFont(QFont("Segoe UI", 8))
        self.lbl_cand_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;")
        name_box.addWidget(self.lbl_cand_subtitle)

        self.lbl_cand_loc = QLabel("📍 Jacksonville, Florida, United States")
        self.lbl_cand_loc.setFont(QFont("Segoe UI", 7))
        self.lbl_cand_loc.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent; border: none;")
        name_box.addWidget(self.lbl_cand_loc)

        entity_header.addLayout(name_box)
        latest_layout.addLayout(entity_header)

        # Confidence Score Matrix
        csm_head = QHBoxLayout()
        lbl_csm = QLabel("CONFIDENCE SCORE MATRIX")
        lbl_csm.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_csm.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        csm_head.addWidget(lbl_csm)

        csm_head.addStretch()

        self.lbl_conf_val = QLabel("AGGREGATE: 91.2%")
        self.lbl_conf_val.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_conf_val.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        csm_head.addWidget(self.lbl_conf_val)
        latest_layout.addLayout(csm_head)

        # Per-Field Confidence Meters
        self.meter_name = ConfidenceMeter("Name: Danielle Mason", 95)
        self.meter_title = ConfidenceMeter("Title: People Operations Specialist", 90)
        self.meter_company = ConfidenceMeter("Company: Moyo", 90)
        self.meter_loc = ConfidenceMeter("Location: Jacksonville, FL", 85)
        latest_layout.addWidget(self.meter_name)
        latest_layout.addWidget(self.meter_title)
        latest_layout.addWidget(self.meter_company)
        latest_layout.addWidget(self.meter_loc)

        # Gating Assertions Checklist
        lbl_chk_title = QLabel("GATING ASSERTIONS")
        lbl_chk_title.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_chk_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding-top: 4px;")
        latest_layout.addWidget(lbl_chk_title)

        latest_layout.addWidget(self._create_checklist_item("■", "Person profile detected", True))
        latest_layout.addWidget(self._create_checklist_item("■", "Identity evidence valid", True))
        latest_layout.addWidget(self._create_checklist_item("■", "Duplicate check passed", True))
        latest_layout.addWidget(self._create_checklist_item("■", "Cloud sync'd #131", True))

        # Open record button
        self.btn_open_record = QPushButton("Open record →")
        self.btn_open_record.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_open_record.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_record.setFixedHeight(34)
        self.btn_open_record.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: #FFFFFF;
                border: 1px solid #FFFFFF;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                color: #0E0E0E;
            }}
        """)
        self.btn_open_record.clicked.connect(self._on_open_record_clicked)
        latest_layout.addWidget(self.btn_open_record)

        right_col.addWidget(card_latest)

        # Storage Daemon Status Card
        card_daemon = Card()
        daemon_l = QVBoxLayout(card_daemon)
        daemon_l.setContentsMargins(14, 10, 14, 10)
        daemon_l.setSpacing(6)

        d_head = QHBoxLayout()
        lbl_dh = QLabel("STORAGE DAEMON STATUS")
        lbl_dh.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_dh.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        d_head.addWidget(lbl_dh)

        d_head.addStretch()

        lbl_dst = QLabel("[ OK // STEADY ]")
        lbl_dst.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_dst.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        d_head.addWidget(lbl_dst)
        daemon_l.addLayout(d_head)

        d_body = QHBoxLayout()
        dot_d = QLabel("■")
        dot_d.setFont(QFont("Consolas", 7))
        dot_d.setStyleSheet("color: #FFFFFF;")
        d_body.addWidget(dot_d)

        lbl_db_info = QLabel("0 DURABLE • All 131 records uploaded • No errors")
        lbl_db_info.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_db_info.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        d_body.addWidget(lbl_db_info)
        d_body.addStretch()
        daemon_l.addLayout(d_body)

        d_foot = QHBoxLayout()
        lbl_df_l = QLabel("Disk commit latency: 0.8ms")
        lbl_df_l.setFont(QFont("Consolas", 7))
        lbl_df_l.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        d_foot.addWidget(lbl_df_l)

        d_foot.addStretch()

        lbl_df_r = QLabel("HASH: d2f89...b14")
        lbl_df_r.setFont(QFont("Consolas", 7))
        lbl_df_r.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        d_foot.addWidget(lbl_df_r)
        daemon_l.addLayout(d_foot)

        right_col.addWidget(card_daemon)

        # Sync Queue Status Card
        card_sync = Card()
        sync_l = QVBoxLayout(card_sync)
        sync_l.setContentsMargins(14, 10, 14, 10)
        sync_l.setSpacing(6)

        s_head = QHBoxLayout()
        lbl_sh = QLabel("SYNC QUEUE STATUS")
        lbl_sh.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_sh.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        s_head.addWidget(lbl_sh)

        s_head.addStretch()

        self.lbl_sync_st = QLabel("[ IDLE ]")
        self.lbl_sync_st.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        self.lbl_sync_st.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        s_head.addWidget(self.lbl_sync_st)
        sync_l.addLayout(s_head)

        s_body = QHBoxLayout()
        self.lbl_sync_pending = QLabel("Pending: 0")
        self.lbl_sync_pending.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.lbl_sync_pending.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        s_body.addWidget(self.lbl_sync_pending)
        
        self.lbl_sync_failed = QLabel("Failed: 0")
        self.lbl_sync_failed.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.lbl_sync_failed.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        s_body.addWidget(self.lbl_sync_failed)
        s_body.addStretch()
        sync_l.addLayout(s_body)

        s_foot = QHBoxLayout()
        self.lbl_sync_time = QLabel("Last Sync: Never")
        self.lbl_sync_time.setFont(QFont("Consolas", 7))
        self.lbl_sync_time.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        s_foot.addWidget(self.lbl_sync_time)
        s_foot.addStretch()
        sync_l.addLayout(s_foot)
        
        right_col.addWidget(card_sync)
        cols_layout.addLayout(right_col, stretch=5)

        main_layout.addLayout(cols_layout)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def update_sync_status(self, pending: int, failed: int, last_sync: str):
        self.lbl_sync_pending.setText(f"Pending: {pending}")
        self.lbl_sync_failed.setText(f"Failed: {failed}")
        self.lbl_sync_time.setText(f"Last Sync: {last_sync}")
        if pending > 0 or failed > 0:
            self.lbl_sync_st.setText("[ ACTIVE ]")
        else:
            self.lbl_sync_st.setText("[ IDLE ]")

    def update_process_load_hud(
        self,
        cpu_pct: float = 0.0,
        mem_mb: float = 0.0,
        latency_ms: float = 0.0,
        queue_depth: int = 0,
        load_level: str = "OPTIMAL",
        state_label: str = "Optimal Execution"
    ):
        """Dynamically renders real-time process load vitals onto the Obsidian Executive HUD."""
        load_level = (load_level or "OPTIMAL").upper()
        color_map = {
            "OPTIMAL": ("#10B981", "rgba(16, 185, 129, 0.15)", "rgba(16, 185, 129, 0.4)"),
            "ACTIVE": ("#38BDF8", "rgba(56, 189, 248, 0.15)", "rgba(56, 189, 248, 0.4)"),
            "BURST": ("#F59E0B", "rgba(245, 158, 11, 0.15)", "rgba(245, 158, 11, 0.4)"),
            "THROTTLED": ("#A855F7", "rgba(168, 85, 247, 0.15)", "rgba(168, 85, 247, 0.4)"),
        }
        text_color, bg_color, border_color = color_map.get(load_level, color_map["OPTIMAL"])

        if hasattr(self, "lbl_load_dot"):
            self.lbl_load_dot.setStyleSheet(f"color: {text_color};")
        if hasattr(self, "lbl_hud_load_pill"):
            self.lbl_hud_load_pill.setText(load_level)
            self.lbl_hud_load_pill.setStyleSheet(f"""
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 3px;
                padding: 1px 6px;
            """)
        if hasattr(self, "lbl_hud_cpu"):
            self.lbl_hud_cpu.setText(f"CPU: {cpu_pct:.1f}%")
        if hasattr(self, "lbl_hud_ram"):
            self.lbl_hud_ram.setText(f"RAM: {mem_mb:.1f} MB")
        if hasattr(self, "lbl_hud_latency"):
            self.lbl_hud_latency.setText(f"LATENCY: {latency_ms:.1f}ms")
        if hasattr(self, "lbl_hud_queue"):
            self.lbl_hud_queue.setText(f"QUEUE: {queue_depth} PENDING")
        if hasattr(self, "lbl_hud_state"):
            self.lbl_hud_state.setText(f"ENGINE: {state_label.upper()}")

    def _create_monochrome_stat(self, title: str, count: str, sub: str) -> QWidget:
        box = Card()
        box.setFixedHeight(95)
        l = QVBoxLayout(box)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px; border: none; background: transparent;")
        l.addWidget(lbl_t)

        lbl_c = QLabel(count)
        lbl_c.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
        l.addWidget(lbl_c)

        lbl_s = QLabel(sub)
        lbl_s.setFont(QFont("Consolas", 7))
        lbl_s.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none; background: transparent;")
        l.addWidget(lbl_s)
        return box

    def _create_mini_stat(self, icon: str, count: str, label: str) -> QWidget:
        return self._create_monochrome_stat(label.upper(), count, "")

    def _create_funnel_stage(self, stage_tag: str, count: str, name: str) -> QWidget:
        return self._create_monochrome_stat(f"{stage_tag}: {name}".upper(), count, "")

    def _on_open_record_clicked(self):
        cand_id = getattr(self, "_current_candidate_id", None)
        if not cand_id and CANDIDATES:
            cand_id = CANDIDATES[0].get("id")
        self.open_candidate_requested.emit(cand_id or "danielle-mason")

    def set_latest_candidate(
        self,
        cand_id: str,
        name: str,
        title: str,
        company: str,
        location: str,
        status: str = "CANONICAL",
        confidence: int = 95,
        profile_url: str = "",
        field_confidence: Optional[Dict[str, float]] = None,
    ):
        self._current_candidate_id = cand_id
        self.lbl_cand_name.setText(name)
        comp_str = f"{title} • {company}" if (title and company) else (title or company or "Professional Profile")
        self.lbl_cand_subtitle.setText(comp_str)
        self.lbl_cand_loc.setText(f"📍 {location}" if location else "📍 Remote")
        self.chip_latest.set_state(status.upper())
        initials = "".join([p[0].upper() for p in name.split()[:2] if p]) or "??"
        if hasattr(self, "lbl_avatar"):
            self.lbl_avatar.setText(initials)
        if hasattr(self, "lbl_conf_val"):
            self.lbl_conf_val.setText(f"AGGREGATE: {confidence}%")

        fc = field_confidence or {}
        name_c = int(round(fc.get("name", 0.85 if name else 0.0) * 100)) if name else 0
        title_c = int(round(fc.get("title", 0.75 if title else 0.0) * 100)) if title else 0
        comp_c = int(round(fc.get("company", 0.75 if company else 0.0) * 100)) if company else 0
        loc_c = int(round(fc.get("location", 0.70 if location else 0.0) * 100)) if location else 0

        self.update_meters(
            name=name,
            title=title,
            company=company,
            location=location,
            name_conf=name_c,
            title_conf=title_c,
            comp_conf=comp_c,
            loc_conf=loc_c,
            cand_id=cand_id,
        )

    def update_meters(
        self,
        name: str,
        title: str,
        company: str,
        location: str,
        name_conf: int = 0,
        title_conf: int = 0,
        comp_conf: int = 0,
        loc_conf: int = 0,
        cand_id: Optional[str] = None
    ):
        if cand_id:
            self._current_candidate_id = cand_id

        name_label = name if (name and name_conf > 0) else "Not detected"
        title_label = title if (title and title_conf > 0) else "Not detected"
        comp_label = company if (company and comp_conf > 0) else "Not detected"
        loc_label = location if (location and loc_conf > 0) else "Not detected"

        self.meter_name.set_score(name_conf if (name and name_conf > 0) else 0, _smart_truncate("Name", name_label, 30))
        self.meter_title.set_score(title_conf if (title and title_conf > 0) else 0, _smart_truncate("Title", title_label, 36))
        self.meter_company.set_score(comp_conf if (company and comp_conf > 0) else 0, _smart_truncate("Company", comp_label, 34))
        self.meter_loc.set_score(loc_conf if (location and loc_conf > 0) else 0, _smart_truncate("Location", loc_label, 32))


    def _create_checklist_item(self, icon: str, text: str, passed: bool) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 1, 0, 1)
        l.setSpacing(6)

        lbl_i = QLabel("■" if passed else "□")
        lbl_i.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_i.setStyleSheet("color: #FFFFFF;" if passed else f"color: {COLOR_TEXT_MUTED};")
        lbl_i.setFixedWidth(12)
        l.addWidget(lbl_i)

        lbl_t = QLabel(text)
        lbl_t.setFont(QFont("Segoe UI", 8))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY if passed else COLOR_TEXT_MUTED};")
        l.addWidget(lbl_t)
        l.addStretch()
        return w

    def _on_scan_click(self):
        self.btn_scan.setText("▶ Scanning...")
        QTimer.singleShot(800, lambda: self.btn_scan.setText("▶ Scan now"))
        self.scan_requested.emit()

    def _on_pause_click(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE_HOVER};
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_PRIMARY};
                    border-radius: 6px;
                    padding: 0 12px;
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
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SURFACE_HOVER};
                    border-color: {COLOR_PRIMARY};
                }}
            """)
        self.pause_toggled.emit()

    def _on_sync_click(self):
        self.btn_sync.setText("↻ Syncing...")
        QTimer.singleShot(800, lambda: self.btn_sync.setText("↻ Sync"))
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
        self.current_page = 0
        self.page_size = 20
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
                border: 1px solid #FFFFFF;
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

        # Pagination Controls
        self.pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setStyleSheet(f"background-color: {COLOR_SURFACE_CARD}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_SURFACE_BORDER}; border-radius: 4px; padding: 4px 12px;")
        self.btn_prev.clicked.connect(self._on_prev_page)
        
        self.lbl_page = QLabel("Page 1 of 1")
        self.lbl_page.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        
        self.btn_next = QPushButton("Next")
        self.btn_next.setStyleSheet(f"background-color: {COLOR_SURFACE_CARD}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_SURFACE_BORDER}; border-radius: 4px; padding: 4px 12px;")
        self.btn_next.clicked.connect(self._on_next_page)

        self.pagination_layout.addStretch()
        self.pagination_layout.addWidget(self.btn_prev)
        self.pagination_layout.addWidget(self.lbl_page)
        self.pagination_layout.addWidget(self.btn_next)
        self.pagination_layout.addStretch()
        main_layout.addLayout(self.pagination_layout)

        self._render_candidates()

    def _render_candidates(self):
        # Clear existing
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        # Filter candidates
        filtered_cands = []
        for cand in CANDIDATES:
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
            filtered_cands.append(cand)
            
        total_pages = max(1, (len(filtered_cands) + self.page_size - 1) // self.page_size)
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)
            
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_cands = filtered_cands[start:end]

        row = 0
        col = 0
        for cand in page_cands:
            card = self._create_candidate_card(cand)
            self.cards_grid.addWidget(card, row, col)
            self.cards.append(card)

            col += 1
            if col > 1:  # 2 columns layout like the screenshot
                col = 0
                row += 1

        self.cards_grid.setRowStretch(row + 1, 1)
        
        self.lbl_page.setText(f"Page {self.current_page + 1} of {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)

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
        lbl_av.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: #FFFFFF;
            border-radius: 4px;
            border: 1px solid {COLOR_SURFACE_BORDER};
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
        self.current_page = 0
        self._render_candidates()

    def _on_filter_changed(self, filter_name: str):
        self.active_filter = filter_name
        self.current_page = 0
        self._update_pill_styles()
        self._render_candidates()

    def _on_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_candidates()
            
    def _on_next_page(self):
        self.current_page += 1
        self._render_candidates()

    def _update_pill_styles(self):
        for k, btn in self.pill_buttons.items():
            if k == self.active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(56, 189, 248, 0.12);
                        color: {COLOR_CYAN_ACCENT};
                        border: 1px solid rgba(56, 189, 248, 0.25);
                        border-radius: 6px;
                        padding: 0 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_SURFACE};
                        color: {COLOR_TEXT_MUTED};
                        border: 1px solid {COLOR_SURFACE_BORDER};
                        border-radius: 6px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLOR_SURFACE_HOVER};
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
        btn_back = QPushButton("← All candidates")
        btn_back.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {COLOR_TEXT_SECONDARY};
                text-align: left;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
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
        lbl_av.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: #FFFFFF;
            border-radius: 6px;
            border: 1px solid {COLOR_SURFACE_BORDER};
        """)
        hero_layout.addWidget(lbl_av)

        name_box = QVBoxLayout()
        name_box.setSpacing(3)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        lbl_name = QLabel(cand["name"])
        lbl_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_name.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        name_row.addWidget(lbl_name)

        chip = StateChip(cand["state"])
        name_row.addWidget(chip)
        name_row.addStretch()
        name_box.addLayout(name_row)

        lbl_sub = QLabel(f"{cand['title']} · {cand['company']}")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        name_box.addWidget(lbl_sub)

        lbl_meta_row = QLabel(f"📍 {cand['location']}   🕒 {cand.get('observed', cand.get('time_ago', '2 min ago'))}")
        lbl_meta_row.setFont(QFont("Segoe UI", 8))
        lbl_meta_row.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        name_box.addWidget(lbl_meta_row)

        hero_layout.addLayout(name_box)
        hero_layout.addStretch()

        # Overall confidence box
        conf_box = QFrame()
        conf_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 8px;
            }}
        """)
        conf_layout = QVBoxLayout(conf_box)
        conf_layout.setContentsMargins(14, 8, 14, 8)
        conf_layout.setSpacing(2)
        lbl_c_tag = QLabel("Overall confidence")
        lbl_c_tag.setFont(QFont("Segoe UI", 7))
        lbl_c_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
        conf_layout.addWidget(lbl_c_tag)
        lbl_c_score = QLabel(f"{cand['confidence']}%")
        lbl_c_score.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        lbl_c_score.setStyleSheet(f"color: {COLOR_CANONICAL}; border: none; background: transparent;")
        conf_layout.addWidget(lbl_c_score)
        hero_layout.addWidget(conf_box)

        # Open in LinkedIn Button
        if cand.get("profile_url"):
            btn_open = QPushButton("Open profile ↗")
            btn_open.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            btn_open.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_open.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE};
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_SURFACE_BORDER};
                    border-radius: 6px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SURFACE_HOVER};
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
        extractor_val = prov.get("extractor") or f"{EXTRACTOR_VERSION} (Perceptual + DOM fusion)"
        source_val = prov.get("source") or f"{cand.get('source', 'Desktop Scout')}"
        ts_val = prov.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S UTC")
        device_val = prov.get("device") or "Installation #483"
        for k, v in [("Where seen", source_val),
                     ("When", ts_val),
                     ("Extractor", extractor_val),
                     ("Device", device_val)]:
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
    item_corrected = Signal(str, dict)
    pattern_blacklisted = Signal(str, str)

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
        self.badge_awaiting.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: #FFFFFF;
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 6px;
            padding: 4px 10px;
        """)

        head = PageHead(
            "Review queue",
            "Scout collects observations; it does not manufacture facts. Anything lacking a stable identifier or requiring confirmation lands here.",
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
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Top row: icon + title + buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Severity icon box
        icon_box = QLabel(item["icon"])
        icon_box.setFont(QFont("Segoe UI", 10))
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFixedSize(30, 30)
        icon_box.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: #FFFFFF;
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 6px;
        """)
        top_row.addWidget(icon_box)

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

        top_row.addLayout(text_col)
        top_row.addStretch()

        # Action Buttons container
        actions_box = QWidget()
        act_l = QHBoxLayout(actions_box)
        act_l.setContentsMargins(0, 0, 0, 0)
        act_l.setSpacing(6)

        iid = item["id"]

        btn_app = QPushButton("✓ Approve")
        btn_app.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        btn_app.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_app.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(16, 185, 129, 0.12);
                color: {COLOR_CANONICAL};
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 4px;
                padding: 3px 10px;
            }}
            QPushButton:hover {{
                background-color: rgba(16, 185, 129, 0.20);
            }}
        """)
        btn_app.clicked.connect(lambda checked=False, i=iid, c=card, a=actions_box: self._on_approve(i, c, a))
        act_l.addWidget(btn_app)

        btn_corr = QPushButton("✎ Correct")
        btn_corr.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
        btn_corr.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_corr.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
            }}
        """)
        btn_corr.clicked.connect(lambda checked=False, it=item, c=card, a=actions_box: self._on_correct(it, c, a))
        act_l.addWidget(btn_corr)

        btn_never = QPushButton("🚫 Never accept")
        btn_never.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
        btn_never.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_never.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(239, 68, 68, 0.08);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.15);
            }}
        """)
        btn_never.clicked.connect(lambda checked=False, it=item, c=card, a=actions_box: self._on_never_accept(it, c, a))
        act_l.addWidget(btn_never)

        btn_dism = QPushButton("✕ Dismiss")
        btn_dism.setFont(QFont("Segoe UI", 7, QFont.Weight.Medium))
        btn_dism.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_dism.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        btn_dism.clicked.connect(lambda checked=False, i=iid, c=card, a=actions_box: self._on_dismiss(i, c, a))
        act_l.addWidget(btn_dism)

        top_row.addWidget(actions_box)
        layout.addLayout(top_row)

        # "Why was this held?" Forensic Reason Panel
        why_held = item.get("why_held") or f"HELD_REASON: {item.get('description', 'Awaiting verified profile identifier')}"
        lbl_why = QLabel(f"🛡️ WHY WAS THIS HELD?  {why_held}")
        lbl_why.setFont(QFont("Consolas", 7))
        lbl_why.setStyleSheet("""
            background-color: rgba(234, 179, 8, 0.06);
            color: #FBBF24;
            border: 1px solid rgba(234, 179, 8, 0.20);
            border-radius: 4px;
            padding: 3px 8px;
        """)
        layout.addWidget(lbl_why)

        return card

    def _on_approve(self, item_id: str, card: QWidget, actions_box: QWidget):
        approve_review_item(item_id)
        actions_box.hide()
        lbl_done = QLabel("✓ Approved to Directory")
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

    def _on_correct(self, item: Dict[str, Any], card: QWidget, actions_box: QWidget):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Correct Fields", f"Correct fields for '{item.get('title')}':", text=item.get("title", ""))
        if ok and text:
            actions_box.hide()
            lbl_done = QLabel(f"✓ Corrected & Approved: {text}")
            lbl_done.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lbl_done.setStyleSheet(f"color: {COLOR_CANONICAL};")
            card.layout().addWidget(lbl_done)
            self.item_corrected.emit(item["id"], {"corrected_name": text})

    def _on_never_accept(self, item: Dict[str, Any], card: QWidget, actions_box: QWidget):
        from scout_desktop.extractor.negative_patterns import add_negative_pattern
        pat = item.get("title", "").split("·")[0].strip()
        add_negative_pattern(pat, pattern_type="name", reason="Flagged 'Never accept' in Desktop Review Queue")
        dismiss_review_item(item["id"])
        actions_box.hide()
        lbl_done = QLabel(f"🚫 Pattern '{pat}' Blacklisted (Auto-rejected in future)")
        lbl_done.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_done.setStyleSheet("color: #f87171;")
        card.layout().addWidget(lbl_done)
        self.pattern_blacklisted.emit(item["id"], pat)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CloudSyncPage (/sync)
# ─────────────────────────────────────────────────────────────────────────────

class _MiniSparklineWidget(QWidget):
    """8-bar monochromatic sparkline matching Stitch design"""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(22)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        bars = [0.30, 0.45, 0.20, 0.60, 0.75, 0.50, 0.85, 1.00]
        n = len(bars)
        gap = 3
        bar_w = max(2, int((w - (gap * (n - 1))) / n))
        
        for i, val in enumerate(bars):
            bx = i * (bar_w + gap)
            bh = int(val * h)
            by = h - bh
            color = QColor("#FFFFFF") if i == n - 1 else QColor("#353535")
            p.fillRect(bx, by, bar_w, bh, color)
        p.end()


class _MiniProgressBarWidget(QWidget):
    """Monochrome thin progress bar matching Stitch card design"""
    def __init__(self, pct: float = 0.5, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pct = max(0.0, min(1.0, pct))
        self.setFixedHeight(4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        # Track
        p.fillRect(0, 0, w, h, QColor("#2A2A2A"))
        # Fill
        fill_w = int(self.pct * w)
        if fill_w > 0:
            p.fillRect(0, 0, fill_w, h, QColor("#FFFFFF"))
        p.end()


class CloudSyncPage(QWidget):
    """
    Cloud Sync Screen matching Stitch Monochrome Command-Center design:
    - Module Tag: MODULE 04 // DATA PIPELINE [AUTONOMOUS]
    - Header with [VERIFY LOGS] and high-contrast [SYNC NOW] button
    - 4 Monochromatic KPI Metric Cards (Queued Buffer, Uploaded Today, Acknowledged, Fatal Failures)
    - Master Split:
      - Left Column (7 cols): Local Queue Stream (FIFO Log, table headers, payload items with status badges, and transaction integrity footer)
      - Right Column (5 cols): Active Fleet Nodes and Offline Resilience 5-Step Architecture
    """
    sync_now_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)

        # ── 1. Page Header Block ──────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(8)

        lbl_module = QLabel("MODULE 04 // DATA PIPELINE")
        lbl_module.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        lbl_module.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 1px;")
        tag_row.addWidget(lbl_module)

        lbl_auto = QLabel("AUTONOMOUS")
        lbl_auto.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_auto.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 4px;
            padding: 1px 6px;
        """)
        tag_row.addWidget(lbl_auto)
        tag_row.addStretch()
        header_text.addLayout(tag_row)

        lbl_title = QLabel("Cloud Sync & Durable Queue")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; text-transform: uppercase; letter-spacing: 0.5px;")
        header_text.addWidget(lbl_title)

        lbl_sub = QLabel("Local-first durable queue: Writes occur locally before background streaming. Cloud is a destination, never a dependency.")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        lbl_sub.setWordWrap(True)
        header_text.addWidget(lbl_sub)

        header_row.addLayout(header_text, stretch=1)

        # Actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.btn_verify_logs = QPushButton("VERIFY LOGS")
        self.btn_verify_logs.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_verify_logs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_verify_logs.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 7px 14px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border-color: {COLOR_SURFACE_BORDER_LIGHT};
            }}
        """)
        actions_row.addWidget(self.btn_verify_logs)

        self.btn_sync_now = QPushButton("SYNC NOW")
        self.btn_sync_now.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_sync_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync_now.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: #0E0E0E;
                border: 1px solid #FFFFFF;
                border-radius: 6px;
                padding: 7px 18px;
            }}
            QPushButton:hover {{
                background-color: #E2E2E2;
            }}
        """)
        self.btn_sync_now.clicked.connect(self._on_sync_now_click)
        actions_row.addWidget(self.btn_sync_now)

        header_row.addLayout(actions_row)
        main_layout.addLayout(header_row)

        # ── 2. Top 4 Monochromatic KPI Metric Cards ────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        # Card 1: Queued Buffer
        kpi_row.addWidget(self._build_kpi_card(
            title="QUEUED BUFFER",
            badge="PENDING",
            value="14",
            sub_label="STORAGE VOL",
            sub_val="54.7 KB",
            progress_pct=0.32,
            foot_left="THRESHOLD CAP",
            foot_right="1,000 MAX"
        ))

        # Card 2: Uploaded Today (with Sparkline)
        kpi_row.addWidget(self._build_kpi_card(
            title="UPLOADED TODAY",
            badge="+12/HR",
            value="49",
            sub_label="PAYLOAD SUM",
            sub_val="1.82 MB",
            use_sparkline=True,
            foot_left="AVG CHUNK RATE",
            foot_right="4.1 MSG/MIN"
        ))

        # Card 3: Acknowledged
        kpi_row.addWidget(self._build_kpi_card(
            title="ACKNOWLEDGED",
            badge="95.9%",
            value="47",
            sub_label="P99 LATENCY",
            sub_val="112 MS",
            progress_pct=0.96,
            foot_left="TRANSACTION INTEGRITY",
            foot_right="SHA-256 MATCH"
        ))

        # Card 4: Fatal Failures
        kpi_row.addWidget(self._build_kpi_card(
            title="FATAL FAILURES",
            badge="NOMINAL",
            value="0",
            sub_label="DEAD LETTER",
            sub_val="0 ROWS",
            progress_pct=0.00,
            foot_left="ERROR COEFFICIENT",
            foot_right="0.0000 %"
        ))

        main_layout.addLayout(kpi_row)

        # ── 3. Master Technical Split (2 Columns) ─────────────────────────
        two_col = QHBoxLayout()
        two_col.setSpacing(16)

        # Left Column (7 cols): Local Queue Stream
        card_lq = Card()
        lq_layout = QVBoxLayout(card_lq)
        lq_layout.setContentsMargins(16, 14, 16, 14)
        lq_layout.setSpacing(10)

        # Local Queue Stream Header
        lq_head = QHBoxLayout()
        lq_head.setSpacing(8)

        dot = QLabel("■")
        dot.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        dot.setStyleSheet("color: #FFFFFF;")
        lq_head.addWidget(dot)

        lbl_lq_title = QLabel("LOCAL QUEUE STREAM")
        lbl_lq_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_lq_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        lq_head.addWidget(lbl_lq_title)

        lbl_fifo = QLabel("FIFO LOG")
        lbl_fifo.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_fifo.setFixedHeight(20)
        lbl_fifo.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: {COLOR_TEXT_MUTED};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 5px;
        """)
        lq_head.addWidget(lbl_fifo, alignment=Qt.AlignmentFlag.AlignVCenter)

        lq_head.addStretch()

        retry_pill = QLabel("↻ RETRY IN 2s")
        retry_pill.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        retry_pill.setFixedHeight(22)
        retry_pill.setStyleSheet(f"""
            background-color: {COLOR_BG_BASE};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 4px;
            padding: 2px 7px;
        """)
        lq_head.addWidget(retry_pill, alignment=Qt.AlignmentFlag.AlignVCenter)

        lbl_pause = QLabel("PAUSE")
        lbl_pause.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        lbl_pause.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; padding-left: 6px;")
        lq_head.addWidget(lbl_pause, alignment=Qt.AlignmentFlag.AlignVCenter)

        lq_layout.addLayout(lq_head)

        # Table Column Headers
        th_box = QFrame()
        th_box.setStyleSheet(f"background-color: {COLOR_SURFACE_ACTIVE}; border-radius: 4px; padding: 2px 0;")
        th_layout = QHBoxLayout(th_box)
        th_layout.setContentsMargins(10, 4, 10, 4)

        lbl_th1 = QLabel("PAYLOAD IDENTIFIER & TYPE")
        lbl_th1.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_th1.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        th_layout.addWidget(lbl_th1, stretch=3)

        lbl_th2 = QLabel("WEIGHT / ATTEMPTS")
        lbl_th2.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_th2.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        th_layout.addWidget(lbl_th2, stretch=2, alignment=Qt.AlignmentFlag.AlignRight)

        lbl_th3 = QLabel("STATE")
        lbl_th3.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_th3.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        th_layout.addWidget(lbl_th3, stretch=2, alignment=Qt.AlignmentFlag.AlignRight)

        lq_layout.addWidget(th_box)

        # 6 Queue Items matching Stitch design
        queue_items = [
            ("Sarah Chen", "ENTITY // PERSON", "4.2 KB", "1 ATTEMPT", "[UPLOADING]", "#FFFFFF", "#0E0E0E"),
            ("Marcus Webb", "ENTITY // PERSON", "3.8 KB", "0 ATTEMPTS", "[QUEUED]", "#2A2A2A", "#FFFFFF"),
            ("Northwind Systems", "ENTITY // COMPANY", "2.1 KB", "0 ATTEMPTS", "[QUEUED]", "#2A2A2A", "#FFFFFF"),
            ("Senior Data Engineer", "ENTITY // JOB_REQ", "5.6 KB", "0 ATTEMPTS", "[QUEUED]", "#2A2A2A", "#FFFFFF"),
            ("Daniel Ortiz", "ENTITY // PERSON", "4.0 KB", "3 ATTEMPTS", "[RETRYING]", "#353535", "#FFFFFF"),
            ("Raw capture #4127", "OBSERVATION // TELEMETRY", "38.0 KB", "SCHEMA HOLD", "[HELD]", "#1F1F1F", "#8E9192")
        ]

        for name, kind, weight, attempts, state_str, bg_pill, fg_pill in queue_items:
            row_frame = QFrame()
            row_frame.setFixedHeight(48)
            row_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLOR_BG_BASE};
                    border-bottom: 1px solid #1F1F1F;
                    border-radius: 4px;
                }}
                QFrame:hover {{
                    background-color: {COLOR_SURFACE_CARD};
                }}
            """)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 4, 12, 4)

            # Col 1: Name & Type
            col1 = QVBoxLayout()
            col1.setSpacing(2)
            lbl_n = QLabel(name)
            lbl_n.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl_n.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
            col1.addWidget(lbl_n)

            lbl_k = QLabel(kind)
            lbl_k.setFont(QFont("Consolas", 7))
            lbl_k.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
            col1.addWidget(lbl_k)
            row_layout.addLayout(col1, stretch=3)

            # Col 2: Weight & Attempts
            col2 = QVBoxLayout()
            col2.setSpacing(2)
            lbl_w = QLabel(weight)
            lbl_w.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            lbl_w.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
            col2.addWidget(lbl_w, alignment=Qt.AlignmentFlag.AlignRight)

            lbl_a = QLabel(attempts)
            lbl_a.setFont(QFont("Consolas", 7))
            lbl_a.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
            col2.addWidget(lbl_a, alignment=Qt.AlignmentFlag.AlignRight)
            row_layout.addLayout(col2, stretch=2)

            # Col 3: Status Badge
            lbl_st = QLabel(state_str)
            lbl_st.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            lbl_st.setStyleSheet(f"""
                background-color: {bg_pill};
                color: {fg_pill};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 3px 8px;
            """)
            row_layout.addWidget(lbl_st, stretch=2, alignment=Qt.AlignmentFlag.AlignRight)

            lq_layout.addWidget(row_frame)

        # Queue Footer Diagnostic Box
        foot_box = QFrame()
        foot_box.setStyleSheet(f"background-color: {COLOR_SURFACE_CARD}; border-top: 1px solid {COLOR_SURFACE_BORDER}; border-radius: 4px; padding: 4px 0;")
        fb_layout = QHBoxLayout(foot_box)
        fb_layout.setContentsMargins(10, 6, 10, 6)

        lbl_foot_left = QLabel("🛡️ Survives network outages, app restarts & device resets.")
        lbl_foot_left.setFont(QFont("Segoe UI", 8))
        lbl_foot_left.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        fb_layout.addWidget(lbl_foot_left)

        fb_layout.addStretch()

        lbl_foot_right = QLabel("TX LOG ID: 0x9E21...4FA")
        lbl_foot_right.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        lbl_foot_right.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        fb_layout.addWidget(lbl_foot_right)

        lq_layout.addWidget(foot_box)
        two_col.addWidget(card_lq, stretch=7)

        # Right Column (5 cols): Fleet Nodes & Offline Resilience
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # ── Right Card 1: Active Fleet Nodes ──
        card_fleet = Card()
        fl_layout = QVBoxLayout(card_fleet)
        fl_layout.setContentsMargins(14, 12, 14, 12)
        fl_layout.setSpacing(6)

        fl_head = QHBoxLayout()
        lbl_fl_title = QLabel("ACTIVE FLEET NODES")
        lbl_fl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_fl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; letter-spacing: 0.5px;")
        fl_head.addWidget(lbl_fl_title)

        fl_head.addStretch()

        lbl_fl_reg = QLabel("5 REGISTERED")
        lbl_fl_reg.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_fl_reg.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_HOVER};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_SURFACE_BORDER};
            border-radius: 3px;
            padding: 1px 6px;
        """)
        fl_head.addWidget(lbl_fl_reg)
        fl_layout.addLayout(fl_head)

        fleet_nodes = [
            ("Abhishek J.", "Windows 11 • v2.8.2", "[HEALTHY]", True),
            ("Ayesha K.", "Windows 11 • v2.8.2", "[HEALTHY]", True),
            ("Tom R.", "macOS 15 • v2.7.1", "[UPDATE]", False),
            ("Lena V.", "Windows 10 • v2.7.1", "[OFFLINE]", False),
            ("Sam O.", "macOS 15 • v2.6.4", "[REQUIRED]", False)
        ]

        for name, os_ver, status_str, is_healthy in fleet_nodes:
            f_frame = QFrame()
            f_frame.setFixedHeight(34)
            f_frame.setStyleSheet("background: transparent; border-bottom: 1px solid #1F1F1F;")
            f_row = QHBoxLayout(f_frame)
            f_row.setContentsMargins(4, 2, 4, 2)
            f_row.setSpacing(8)

            dot_fl = QLabel("■")
            dot_fl.setFont(QFont("Consolas", 7))
            dot_fl.setStyleSheet("color: #FFFFFF; border: none; background: transparent;" if is_healthy else f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
            f_row.addWidget(dot_fl)

            col_dev = QVBoxLayout()
            col_dev.setSpacing(1)
            lbl_dn = QLabel(name)
            lbl_dn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            lbl_dn.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
            col_dev.addWidget(lbl_dn)

            lbl_dos = QLabel(os_ver)
            lbl_dos.setFont(QFont("Consolas", 7))
            lbl_dos.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
            col_dev.addWidget(lbl_dos)
            f_row.addLayout(col_dev)

            f_row.addStretch()

            lbl_fst = QLabel(status_str)
            lbl_fst.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            lbl_fst.setStyleSheet(f"""
                background-color: {COLOR_SURFACE_ACTIVE if is_healthy else COLOR_SURFACE_CARD};
                color: {COLOR_TEXT_PRIMARY if is_healthy else COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 3px;
                padding: 1px 6px;
            """)
            f_row.addWidget(lbl_fst)
            fl_layout.addWidget(f_frame)

        fl_foot = QLabel("CONSENSUS PROTOCOL: PBFT // 4 OF 5 QUORUM")
        fl_foot.setFont(QFont("Consolas", 7))
        fl_foot.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border-top: 1px solid {COLOR_SURFACE_BORDER}; padding-top: 6px;")
        fl_layout.addWidget(fl_foot)

        right_col.addWidget(card_fleet)

        # ── Right Card 2: Offline Resilience Architecture ──
        card_res = Card()
        res_layout = QVBoxLayout(card_res)
        res_layout.setContentsMargins(14, 12, 14, 12)
        res_layout.setSpacing(8)

        res_head = QHBoxLayout()
        lbl_res_title = QLabel("OFFLINE RESILIENCE ARCHITECTURE")
        lbl_res_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_res_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; letter-spacing: 0.5px;")
        res_head.addWidget(lbl_res_title)

        res_head.addStretch()

        lbl_spec = QLabel("SPEC 4.1")
        lbl_spec.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_spec.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        res_head.addWidget(lbl_spec)
        res_layout.addLayout(res_head)

        res_steps = [
            ("1", "Local-First Write Boundary", "All telemetry, scraped entities, and candidate reviews write instantly to the local SQLite WAL ring. Zero synchronous network dependencies on capture path."),
            ("2", "Deterministic Serialization", "Records compile into immutable Protobuf packets with local sequence keys (seq_id). Payloads checksummed via SHA-256 before buffering."),
            ("3", "Background Micro-Streaming", "Worker thread polls local journal every 500ms. If upstream is saturated or dead, worker sleeps silently without UI degradation."),
            ("4", "Exponential Jittered Backoff", "Transient gateway failures trigger backoff (2^n + jitter). Retries capped at 5 attempts before quarantine into schema hold."),
            ("5", "Two-Phase Cloud Ingestion", "Central cluster validates integrity token and emits atomic ACK. Only upon confirmation is the local record dequeued.")
        ]

        for step_num, step_title, step_desc in res_steps:
            step_frame = QFrame()
            step_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLOR_BG_BASE};
                    border: 1px solid #1F1F1F;
                    border-radius: 6px;
                }}
                QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            st_box = QHBoxLayout(step_frame)
            st_box.setContentsMargins(10, 8, 10, 8)
            st_box.setSpacing(10)

            lbl_num = QLabel(step_num)
            lbl_num.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_num.setFixedSize(20, 20)
            lbl_num.setStyleSheet(f"""
                background-color: {"#FFFFFF" if step_num == "1" else COLOR_SURFACE_HOVER};
                color: {"#0E0E0E" if step_num == "1" else COLOR_TEXT_PRIMARY};
                border-radius: 4px;
            """)
            st_box.addWidget(lbl_num, alignment=Qt.AlignmentFlag.AlignTop)

            st_col = QVBoxLayout()
            st_col.setSpacing(2)
            lbl_stt = QLabel(step_title)
            lbl_stt.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_stt.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
            st_col.addWidget(lbl_stt)

            lbl_std = QLabel(step_desc)
            lbl_std.setFont(QFont("Segoe UI", 7))
            lbl_std.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; border: none; background: transparent;")
            lbl_std.setWordWrap(True)
            st_col.addWidget(lbl_std)
            st_box.addLayout(st_col, stretch=1)

            res_layout.addWidget(step_frame)

        right_col.addWidget(card_res)
        two_col.addLayout(right_col, stretch=5)

        main_layout.addLayout(two_col)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _build_kpi_card(
        self,
        title: str,
        badge: str,
        value: str,
        sub_label: str,
        sub_val: str,
        progress_pct: Optional[float] = None,
        use_sparkline: bool = False,
        foot_left: str = "",
        foot_right: str = ""
    ) -> QWidget:
        card = Card()
        card.setFixedHeight(120)
        l = QVBoxLayout(card)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(4)

        # Header Row
        h_row = QHBoxLayout()
        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; letter-spacing: 0.5px;")
        h_row.addWidget(lbl_t)

        h_row.addStretch()

        lbl_b = QLabel(badge)
        lbl_b.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_b.setStyleSheet(f"""
            background-color: {COLOR_SURFACE_ACTIVE};
            color: {COLOR_TEXT_PRIMARY};
            border-radius: 3px;
            padding: 1px 5px;
        """)
        h_row.addWidget(lbl_b)
        l.addLayout(h_row)

        # Center Value Row
        c_row = QHBoxLayout()
        lbl_val = QLabel(value)
        lbl_val.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        c_row.addWidget(lbl_val)

        c_row.addStretch()

        sub_box = QVBoxLayout()
        sub_box.setSpacing(0)
        lbl_sl = QLabel(sub_label)
        lbl_sl.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        lbl_sl.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        sub_box.addWidget(lbl_sl, alignment=Qt.AlignmentFlag.AlignRight)

        lbl_sv = QLabel(sub_val)
        lbl_sv.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        lbl_sv.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        sub_box.addWidget(lbl_sv, alignment=Qt.AlignmentFlag.AlignRight)
        c_row.addLayout(sub_box)
        l.addLayout(c_row)

        # Visual indicator: Progress bar or sparkline
        if use_sparkline:
            spark = _MiniSparklineWidget()
            l.addWidget(spark)
        elif progress_pct is not None:
            bar = _MiniProgressBarWidget(progress_pct)
            l.addWidget(bar)

        # Footer Row
        f_row = QHBoxLayout()
        lbl_fl = QLabel(foot_left)
        lbl_fl.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
        lbl_fl.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        f_row.addWidget(lbl_fl)

        f_row.addStretch()

        lbl_fr = QLabel(foot_right)
        lbl_fr.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        lbl_fr.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        f_row.addWidget(lbl_fr)
        l.addLayout(f_row)

        return card

    def _on_sync_now_click(self):
        self.btn_sync_now.setText("SYNCING...")
        QTimer.singleShot(800, lambda: self.btn_sync_now.setText("SYNC NOW"))
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
                background-color: {COLOR_SURFACE_HOVER};
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

        # Scroll Area for activity cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {COLOR_BG_BASE}; border: none; }} QScrollArea > QWidget {{ background-color: {COLOR_BG_BASE}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(8)

        self._render_feed()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _get_unread_count(self) -> int:
        return sum(1 for a in ACTIVITY_FEED if a.get("unread"))

    def _update_pill_styles(self):
        for key, btn in self.pill_buttons.items():
            if key == self.active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_SURFACE_ACTIVE};
                        color: {COLOR_PRIMARY};
                        border: 1px solid {COLOR_PRIMARY};
                        border-radius: 14px;
                        padding: 0 12px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_SURFACE_CARD};
                        color: {COLOR_TEXT_MUTED};
                        border: 1px solid {COLOR_SURFACE_BORDER};
                        border-radius: 14px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLOR_SURFACE_HOVER};
                        color: {COLOR_TEXT_PRIMARY};
                    }}
                """)

    def _render_feed(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtered = []
        for a in ACTIVITY_FEED:
            if self.active_filter == "ALL":
                filtered.append(a)
            elif self.active_filter == "UNREAD" and a.get("unread"):
                filtered.append(a)
            elif self.active_filter == "DECISIONS" and a.get("category") == "decision":
                filtered.append(a)
            elif self.active_filter == "WARNINGS" and a.get("severity") == "warn":
                filtered.append(a)
            elif self.active_filter == "ERRORS" and a.get("severity") == "error":
                filtered.append(a)

        for act in filtered:
            self.cards_layout.addWidget(self._create_activity_card(act))

        self.cards_layout.addStretch()

    def _create_activity_card(self, act: Dict[str, Any]) -> QWidget:
        card = Card()
        card.setFixedHeight(56)
        l = QHBoxLayout(card)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(10)

        # Left Icon Circle Badge
        icon_box = QLabel(act.get("icon", "•"))
        icon_box.setFont(QFont("Segoe UI", 9))
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFixedSize(26, 26)

        sev = act.get("severity", "info")
        if sev in ("success", "warn"):
            bg = COLOR_SURFACE_HOVER
            fg = "#FFFFFF"
            border = COLOR_SURFACE_BORDER
        elif sev == "error":
            bg = COLOR_SURFACE_CARD
            fg = COLOR_TEXT_MUTED
            border = COLOR_SURFACE_BORDER
        else:
            bg = COLOR_SURFACE_CARD
            fg = COLOR_TEXT_PRIMARY
            border = COLOR_SURFACE_BORDER

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

        return card

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
        self.btn_claim.setFixedHeight(40)
        self.btn_claim.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_claim.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #0B0F19;
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
        self.btn_account_signin.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        self.btn_account_signin.setFixedHeight(40)
        self.btn_account_signin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_account_signin.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SURFACE_HOVER};
            }}
        """)
        self.btn_account_signin.clicked.connect(self._on_account_signin_click)
        card_layout.addWidget(self.btn_account_signin)

        # Success Message Widget (Hidden by default, shown on successful claim)
        self.success_widget = QWidget()
        sw_layout = QVBoxLayout(self.success_widget)
        sw_layout.setContentsMargins(0, 10, 0, 10)
        sw_layout.setSpacing(10)
        sw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        shield_icon = QLabel("🛡️")
        shield_icon.setFont(QFont("Segoe UI", 16))
        shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield_icon.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15);
            color: {COLOR_CANONICAL};
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.30);
            min-width: 40px;
            min-height: 40px;
            max-width: 40px;
            max-height: 40px;
        """)
        sw_layout.addWidget(shield_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_success = QLabel("Device claimed")
        self.lbl_success.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_success.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_success.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        sw_layout.addWidget(self.lbl_success)

        self.lbl_success_sub = QLabel("Installation #483 · WIN-PRASHANT-01 is now linked to prashant@talentops.ai.")
        self.lbl_success_sub.setFont(QFont("Segoe UI", 8))
        self.lbl_success_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_success_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        self.lbl_success_sub.setWordWrap(True)
        sw_layout.addWidget(self.lbl_success_sub)

        self.btn_start_observing = QPushButton("Start observing")
        self.btn_start_observing.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_start_observing.setFixedHeight(40)
        self.btn_start_observing.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_start_observing.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #0B0F19;
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
        lbl_foot = QLabel(DEVICE_CLAIM_STATE.get("footer", f"Scout v{__version__} · Extractor {EXTRACTOR_VERSION} · Edge intelligence agent"))
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
            user_str = res.get("user") or "prashant@talentops.ai"
            inst_str = res.get("installation_id") or "Installation #483"
            self.lbl_success.setText("Device claimed")
            self.lbl_success_sub.setText(f"{inst_str} · WIN-PRASHANT-01 is now linked to {user_str}.")
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

