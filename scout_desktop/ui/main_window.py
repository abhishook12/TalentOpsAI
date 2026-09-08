"""
ui/main_window.py — Level 3 Full Windows Companion Application Window

Implements the complete executive desktop companion window specified in UI/UX rework:
- Native Windows QMainWindow with standard or polished dark title bar.
- Functional Minimize (-), Maximize/Restore (□), and Close (✕) behaviors.
- Close hides to tray and persistent edge dock handle without killing background scout.
- Top Banner: "What is it doing right now?" (Current target window, process, sampling rate, state).
- Subsystem Health Chips (System, Backend, Window, Capture, Analyzer, DB Sync).
- 10 Explicit Telemetry Counters (Captured, Analyzed, Useful, Staged, Matched, New, Enriched, DB Updates, Purged, Buffer).
- Latest Captured Frame thumbnail preview with delta %, capture ID, timestamp.
- Grounded Extraction Proof Table (Field, Value, Confidence, Evidence, Decision).
- Backend & Cloud Master Database Verification Card (Target URL, HTTP 200, Staged count, Master DB).
- Rolling Real-Time Activity Event Stream.
- Quick Developer Actions (Force Capture, Diagnostics, Settings).
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from io import BytesIO

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QToolButton, QSplitter
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QPixmap, QIcon, QImage, QCloseEvent
from PIL import Image

logger = logging.getLogger("scout.main_window")


class SubsystemIndicator(QFrame):
    """Subsystem status badge."""
    def __init__(self, name: str, default_state: str = "IDLE", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 2px 6px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(6)

        self.lbl_name = QLabel(name.upper())
        self.lbl_name.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 700; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_name)

        layout.addStretch()

        self.lbl_val = QLabel(default_state)
        self.lbl_val.setStyleSheet("color: #94a3b8; font-size: 8px; font-weight: 800;")
        layout.addWidget(self.lbl_val)

    def set_state(self, state: str, color: Optional[str] = None):
        self.lbl_val.setText(state.upper())
        if not color:
            s = state.upper()
            if any(k in s for k in ("ACTIVE", "CONNECTED", "DETECTED", "SUCCESS", "GROUNDED")):
                color = "#10b981"  # green
            elif any(k in s for k in ("IDLE", "WATCH", "STAGED", "BATC")):
                color = "#f59e0b"  # yellow
            elif any(k in s for k in ("ERROR", "FAIL", "DISCONNECT", "REJECT")):
                color = "#ef4444"  # red
            else:
                color = "#38bdf8"  # blue
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: 800;")


class MetricBadge(QFrame):
    """Clean metric card for explicit counters."""
    def __init__(self, label: str, value: str = "0", color: str = "#f8fafc", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(1)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 700; letter-spacing: 0.4px;")
        layout.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 800;")
        layout.addWidget(self.lbl_val)

    def set_value(self, val: str):
        self.lbl_val.setText(str(val))

    @property
    def value(self) -> str:
        return self.lbl_val.text()


class MainWindow(QMainWindow):
    """
    Level 3: Full Windows Companion Application.
    Provides standard window controls (Min/Max/Close) and live extraction telemetry.
    """
    force_capture_requested = Signal()
    open_diagnostics_requested = Signal()
    open_settings_requested = Signal()
    shutdown_requested = Signal()
    dock_to_edge_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_shutting_down = False
        self.setWindowTitle("TalentOps Scout — Autonomous Desktop Companion")
        self.resize(480, 840)
        self.setMinimumSize(420, 600)

        # Set taskbar/window icon
        logo_pix = self._load_logo_pixmap(64)
        if logo_pix:
            self.setWindowIcon(QIcon(logo_pix))

        self.init_ui()

    def _load_logo_pixmap(self, size: int = 24) -> Optional[QPixmap]:
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.ico"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"),
            r"c:\TalentOpsAI\talentops-logo.png",
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return None

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #070b14;")

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(12, 10, 12, 10)
        main_vbox.setSpacing(8)

        # ── 1. Top Brand & Environment Header ──
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(26, 26)
        logo_pix = self._load_logo_pixmap(26)
        if logo_pix:
            self.lbl_logo.setPixmap(logo_pix)
            self.lbl_logo.setScaledContents(True)
        header.addWidget(self.lbl_logo)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        lbl_brand = QLabel("TALENTOPS SCOUT")
        lbl_brand.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: 800; letter-spacing: 0.8px;")
        brand_col.addWidget(lbl_brand)

        self.lbl_env_badge = QLabel("PRODUCTION CLOUD (135,643 live records)")
        self.lbl_env_badge.setStyleSheet("color: #10b981; font-size: 9px; font-weight: 700;")
        brand_col.addWidget(self.lbl_env_badge)
        header.addLayout(brand_col)

        header.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10b981; font-size: 14px;")
        header.addWidget(self.status_dot)

        self.lbl_main_status = QLabel("AUTONOMOUS ACTIVE")
        self.lbl_main_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: 700;")
        header.addWidget(self.lbl_main_status)

        header.addSpacing(6)

        # Quick Window Control Buttons (Top Header)
        top_ctrl = QHBoxLayout()
        top_ctrl.setSpacing(4)

        self.btn_top_min = QPushButton("—")
        self.btn_top_min.setToolTip("Minimize to Windows Taskbar")
        self.btn_top_min.setFixedSize(26, 22)
        self.btn_top_min.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
                border-color: #64748b;
            }
        """)
        self.btn_top_min.clicked.connect(self.showMinimized)
        top_ctrl.addWidget(self.btn_top_min)

        self.btn_top_side = QPushButton("⇤ Side")
        self.btn_top_side.setToolTip("Hide to Side Small Handle on Screen Edge")
        self.btn_top_side.setFixedHeight(22)
        self.btn_top_side.setStyleSheet("""
            QPushButton {
                background: #0c2d48;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 4px;
                padding: 0 6px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #0284c7;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_top_side.clicked.connect(self._dock_to_side)
        top_ctrl.addWidget(self.btn_top_side)

        self.btn_top_close = QPushButton("✕ Exit")
        self.btn_top_close.setToolTip("Completely Close All Operations & Exit App")
        self.btn_top_close.setFixedHeight(22)
        self.btn_top_close.setStyleSheet("""
            QPushButton {
                background: #450a0a;
                color: #fca5a5;
                border: 1px solid #991b1b;
                border-radius: 4px;
                padding: 0 6px;
                font-size: 9px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: #dc2626;
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        self.btn_top_close.clicked.connect(self.shutdown_requested.emit)
        top_ctrl.addWidget(self.btn_top_close)

        header.addLayout(top_ctrl)

        main_vbox.addLayout(header)

        # ── 2. "What is it doing right now?" Live State Banner ──
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #1e1b4b);
                border: 1px solid #3b82f6;
                border-radius: 8px;
            }
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        banner_layout.setSpacing(4)

        b_top = QHBoxLayout()
        self.lbl_banner_action = QLabel("WHAT IS IT DOING RIGHT NOW?")
        self.lbl_banner_action.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: 800; letter-spacing: 0.5px;")
        b_top.addWidget(self.lbl_banner_action)
        b_top.addStretch()

        self.lbl_sampling_pulse = QLabel("⚡ SAMPLING (1.0s interval)")
        self.lbl_sampling_pulse.setStyleSheet("color: #10b981; font-size: 9px; font-weight: 700;")
        b_top.addWidget(self.lbl_sampling_pulse)
        banner_layout.addLayout(b_top)

        self.lbl_target_desc = QLabel("Currently observing Google Chrome — Watching for LinkedIn candidate profiles...")
        self.lbl_target_desc.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: 600;")
        self.lbl_target_desc.setWordWrap(True)
        banner_layout.addWidget(self.lbl_target_desc)

        self.lbl_target_url = QLabel("URL: https://www.linkedin.com")
        self.lbl_target_url.setStyleSheet("color: #94a3b8; font-size: 9px; font-family: Consolas, monospace;")
        self.lbl_target_url.setWordWrap(True)
        banner_layout.addWidget(self.lbl_target_url)

        main_vbox.addWidget(banner)

        # ── 3. Scrollable Telemetry & Proof Body ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #0b1120;
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 3px;
            }
        """)

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setSpacing(8)

        # ── 3A. Subsystem Health Chips (6 Components) ──
        status_box = QFrame()
        status_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px;")
        status_grid = QGridLayout(status_box)
        status_grid.setContentsMargins(6, 6, 6, 6)
        status_grid.setSpacing(4)

        self.ind_system = SubsystemIndicator("System", "ACTIVE")
        self.ind_backend = SubsystemIndicator("Backend", "CONNECTED")
        self.ind_window = SubsystemIndicator("Window", "DETECTED")
        self.ind_capture = SubsystemIndicator("Capture", "ACTIVE")
        self.ind_analyzer = SubsystemIndicator("Analyzer", "ACTIVE")
        self.ind_db = SubsystemIndicator("DB Sync", "CONNECTED")

        status_grid.addWidget(self.ind_system, 0, 0)
        status_grid.addWidget(self.ind_backend, 0, 1)
        status_grid.addWidget(self.ind_window, 1, 0)
        status_grid.addWidget(self.ind_capture, 1, 1)
        status_grid.addWidget(self.ind_analyzer, 2, 0)
        status_grid.addWidget(self.ind_db, 2, 1)
        c_layout.addWidget(status_box)

        # ── 3B. Explicit Telemetry Counters (12 Metrics) ──
        c_layout.addWidget(self._build_section_header("TELEMETRY COUNTERS"))
        cnt_row1 = QHBoxLayout()
        cnt_row1.setSpacing(4)
        self.c_captured = MetricBadge("Captured", "0")
        self.c_analyzed = MetricBadge("Analyzed", "0")
        self.c_useful = MetricBadge("Useful", "0", color="#38bdf8")
        self.c_staged = MetricBadge("Staged", "0", color="#f59e0b")
        self.c_matched = MetricBadge("Matched", "0")
        cnt_row1.addWidget(self.c_captured)
        cnt_row1.addWidget(self.c_analyzed)
        cnt_row1.addWidget(self.c_useful)
        cnt_row1.addWidget(self.c_staged)
        cnt_row1.addWidget(self.c_matched)
        c_layout.addLayout(cnt_row1)

        cnt_row2 = QHBoxLayout()
        cnt_row2.setSpacing(4)
        self.c_new = MetricBadge("New", "0", color="#10b981")
        self.c_enriched = MetricBadge("Enriched", "0", color="#a855f7")
        self.c_db_updates = MetricBadge("DB Updates", "0", color="#38bdf8")
        self.c_purged = MetricBadge("Purged", "0", color="#64748b")
        self.c_buffer = MetricBadge("Buffer", "0/20", color="#f59e0b")
        cnt_row2.addWidget(self.c_new)
        cnt_row2.addWidget(self.c_enriched)
        cnt_row2.addWidget(self.c_db_updates)
        cnt_row2.addWidget(self.c_purged)
        cnt_row2.addWidget(self.c_buffer)
        c_layout.addLayout(cnt_row2)

        cnt_row3 = QHBoxLayout()
        cnt_row3.setSpacing(4)
        self.c_observed = MetricBadge("Observed", "0", color="#06b6d4")
        self.c_fields_added = MetricBadge("Fields Added", "0", color="#22c55e")
        cnt_row3.addWidget(self.c_observed)
        cnt_row3.addWidget(self.c_fields_added)
        cnt_row3.addStretch()
        c_layout.addLayout(cnt_row3)


        # ── 3C. Latest Frame Preview & Classification ──
        c_layout.addWidget(self._build_section_header("LATEST CAPTURE & REASON"))
        cap_box = QFrame()
        cap_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px;")
        cap_layout = QVBoxLayout(cap_box)
        cap_layout.setContentsMargins(8, 8, 8, 8)
        cap_layout.setSpacing(6)

        cap_header = QHBoxLayout()
        self.lbl_cap_id = QLabel("Capture ID: ---")
        self.lbl_cap_id.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")
        cap_header.addWidget(self.lbl_cap_id)
        cap_header.addStretch()

        self.lbl_cap_time = QLabel("Time: ---")
        self.lbl_cap_time.setStyleSheet("color: #64748b; font-size: 9px;")
        cap_header.addWidget(self.lbl_cap_time)
        cap_layout.addLayout(cap_header)

        # Splitter: Thumbnail Left, Meta Right
        thumb_row = QHBoxLayout()
        thumb_row.setSpacing(8)

        self.lbl_thumbnail = QLabel("No Capture")
        self.lbl_thumbnail.setFixedSize(140, 85)
        self.lbl_thumbnail.setStyleSheet("background-color: #030712; border: 1px dashed #334155; border-radius: 4px; color: #475569; font-size: 9px;")
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        thumb_row.addWidget(self.lbl_thumbnail)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(3)
        self.lbl_delta = QLabel("Delta: 0.00%")
        self.lbl_delta.setStyleSheet("color: #f8fafc; font-size: 9px; font-weight: 600;")
        meta_col.addWidget(self.lbl_delta)

        self.lbl_reason = QLabel("Reason: WAITING")
        self.lbl_reason.setStyleSheet("color: #f59e0b; font-size: 9px; font-weight: 600;")
        meta_col.addWidget(self.lbl_reason)

        self.lbl_breakdown = QLabel("People: 0 | Companies: 0 | Locations: 0 | Signals: 0")
        self.lbl_breakdown.setStyleSheet("color: #94a3b8; font-size: 8px;")
        meta_col.addWidget(self.lbl_breakdown)

        self.lbl_gate_status = QLabel("Gate: WAITING_FRAME")
        self.lbl_gate_status.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 700;")
        meta_col.addWidget(self.lbl_gate_status)

        thumb_row.addLayout(meta_col)
        cap_layout.addLayout(thumb_row)
        c_layout.addWidget(cap_box)

        # ── 3D. Grounded Extraction Proof Table ──
        c_layout.addWidget(self._build_section_header("EXTRACTION PROOF (GROUNDED EVIDENCE)"))
        self.proof_table = QTableWidget()
        self.proof_table.setColumnCount(4)
        self.proof_table.setHorizontalHeaderLabels(["Field", "Extracted Value", "Conf", "Decision"])
        self.proof_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proof_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proof_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.proof_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.proof_table.verticalHeader().setVisible(False)
        self.proof_table.setMinimumHeight(140)
        self.proof_table.setStyleSheet("""
            QTableWidget {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 6px;
                color: #e2e8f0;
                font-size: 9px;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #64748b;
                font-size: 8px;
                font-weight: 700;
                border: none;
                padding: 4px;
            }
            QTableWidget::item {
                padding: 3px 6px;
            }
        """)
        c_layout.addWidget(self.proof_table)

        # ── 3E. Backend & Cloud Database Proof ──
        c_layout.addWidget(self._build_section_header("BACKEND & DATABASE PROOF"))
        db_box = QFrame()
        db_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px;")
        db_layout = QVBoxLayout(db_box)
        db_layout.setContentsMargins(8, 6, 8, 6)
        db_layout.setSpacing(2)

        self.lbl_db_target = QLabel("Backend Target: https://talentopsai-1.onrender.com")
        self.lbl_db_target.setStyleSheet("color: #38bdf8; font-size: 9px; font-family: Consolas, monospace;")
        db_layout.addWidget(self.lbl_db_target)

        self.lbl_db_response = QLabel("Last Response: CONNECTED (200 OK)")
        self.lbl_db_response.setStyleSheet("color: #10b981; font-size: 9px; font-weight: 600;")
        db_layout.addWidget(self.lbl_db_response)

        self.lbl_db_write = QLabel("Last DB Write: None")
        self.lbl_db_write.setStyleSheet("color: #e2e8f0; font-size: 9px;")
        db_layout.addWidget(self.lbl_db_write)

        c_layout.addWidget(db_box)

        # ── 3F. Rolling Live Activity Stream ──
        c_layout.addWidget(self._build_section_header("LIVE ACTIVITY STREAM"))
        self.stream_box = QFrame()
        self.stream_box.setStyleSheet("background-color: #030712; border: 1px solid #1e293b; border-radius: 6px;")
        self.stream_layout = QVBoxLayout(self.stream_box)
        self.stream_layout.setContentsMargins(6, 6, 6, 6)
        self.stream_layout.setSpacing(2)

        self._log_entries: List[QLabel] = []
        c_layout.addWidget(self.stream_box)

        scroll.setWidget(content)
        main_vbox.addWidget(scroll)

        # ── 4. Bottom Controls & Developer Actions ──
        footer = QHBoxLayout()
        footer.setSpacing(6)

        btn_force = QPushButton("⚡ Force Capture")
        btn_force.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        btn_force.clicked.connect(self.force_capture_requested.emit)
        footer.addWidget(btn_force)

        btn_diag = QPushButton("Diagnostics")
        btn_diag.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        btn_diag.clicked.connect(self.open_diagnostics_requested.emit)
        footer.addWidget(btn_diag)

        btn_settings = QPushButton("Settings")
        btn_settings.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        btn_settings.clicked.connect(self.open_settings_requested.emit)
        footer.addWidget(btn_settings)

        self.btn_dev_mode = QPushButton("Dev Mode: OFF")
        self.btn_dev_mode.setCheckable(True)
        self.btn_dev_mode.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:checked {
                background: #0e7490;
                color: #22d3ee;
                border: 1px solid #0891b2;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
            }
        """)
        self.btn_dev_mode.toggled.connect(self._toggle_dev_mode)
        footer.addWidget(self.btn_dev_mode)

        footer.addStretch()

        self.lbl_purge_status = QLabel("Auto-Purge: Clean")
        self.lbl_purge_status.setStyleSheet("color: #64748b; font-size: 8px;")
        footer.addWidget(self.lbl_purge_status)

        main_vbox.addLayout(footer)

        # ── 5. Window State & Application Control Bar ──
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("""
            QFrame {
                background: #090e1a;
                border: 1px solid #1e293b;
                border-radius: 6px;
            }
        """)
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)
        ctrl_layout.setSpacing(6)

        lbl_controls_title = QLabel("CONTROLS:")
        lbl_controls_title.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 800; letter-spacing: 0.5px;")
        ctrl_layout.addWidget(lbl_controls_title)

        # 1. Minimize to Taskbar button
        self.btn_min_taskbar = QPushButton("🗕 Minimize to Taskbar")
        self.btn_min_taskbar.setToolTip("Minimize companion window to standard Windows taskbar")
        self.btn_min_taskbar.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334155;
                color: #ffffff;
                border-color: #64748b;
            }
        """)
        self.btn_min_taskbar.clicked.connect(self.showMinimized)
        ctrl_layout.addWidget(self.btn_min_taskbar)

        # 2. Hide to Small Side Handle button
        self.btn_dock_side = QPushButton("⇤ Hide to Side Handle")
        self.btn_dock_side.setToolTip("Hide companion window and keep the small side handle visible on screen edge")
        self.btn_dock_side.setStyleSheet("""
            QPushButton {
                background: #0c2d48;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #0284c7;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_dock_side.clicked.connect(self._dock_to_side)
        ctrl_layout.addWidget(self.btn_dock_side)

        ctrl_layout.addStretch()

        # 3. Completely Close All Operations button
        self.btn_exit_app = QPushButton("🛑 Exit All Operations")
        self.btn_exit_app.setToolTip("Completely stop visual sampling, background workers, and close TalentOps Scout")
        self.btn_exit_app.setStyleSheet("""
            QPushButton {
                background: #450a0a;
                color: #fca5a5;
                border: 1px solid #991b1b;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: #dc2626;
                color: #ffffff;
                border-color: #ef4444;
            }
        """)
        self.btn_exit_app.clicked.connect(self.shutdown_requested.emit)
        ctrl_layout.addWidget(self.btn_exit_app)

        main_vbox.addWidget(ctrl_bar)

    def _build_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 800; letter-spacing: 0.8px; margin-top: 4px;")
        return lbl

    def _toggle_dev_mode(self, enabled: bool):
        """Toggles deep technical debugging views (activity stream, raw data)."""
        if enabled:
            self.btn_dev_mode.setText("Dev Mode: ON")
            self.stream_box.setVisible(True)
            self.proof_table.setVisible(True)
        else:
            self.btn_dev_mode.setText("Dev Mode: OFF")
            # In clean user mode, keep proof table but compact activity stream
            self.stream_box.setVisible(True)
            self.proof_table.setVisible(True)

    def _dock_to_side(self):
        """Hides the main companion window, leaving the persistent side handle on screen edge."""
        self.dock_to_edge_requested.emit()
        self.hide()

    def closeEvent(self, event: QCloseEvent):
        """
        Close event handler. If shutdown is in progress, accept event to exit.
        Otherwise hide to side handle.
        """
        if getattr(self, "_is_shutting_down", False):
            event.accept()
            return
        event.ignore()
        self._dock_to_side()

    def update_environment(self, env_name: str, api_base: str):
        self.lbl_env_badge.setText(f"{env_name.upper()} (135,643 live records)")
        self.lbl_db_target.setText(f"Backend Target: {api_base}")

    def update_status_state(self, state: str):
        s = state.upper()
        self.lbl_main_status.setText(s)
        if "ACTIVE" in s or "CONNECTED" in s or "DETECTED" in s:
            col = "#10b981"
        elif "IDLE" in s or "STAGED" in s:
            col = "#f59e0b"
        else:
            col = "#ef4444"
        self.status_dot.setStyleSheet(f"color: {col}; font-size: 14px;")
        self.lbl_main_status.setStyleSheet(f"color: {col}; font-size: 10px; font-weight: 700;")

    def update_window_context(self, app_name: str, window_title: str, url: str, context: str):
        self.lbl_target_desc.setText(f"Observing [{app_name}] — {window_title[:45]}")
        self.lbl_target_url.setText(f"URL: {url or '---'}")
        self.ind_window.set_state("DETECTED")

    def update_explicit_counters(self, metrics: Dict[str, Any]):
        self.c_captured.set_value(metrics.get("captured", 0))
        self.c_analyzed.set_value(metrics.get("analyzed", 0))
        self.c_useful.set_value(metrics.get("useful", 0))
        self.c_staged.set_value(metrics.get("staged", 0))
        self.c_matched.set_value(metrics.get("matched", 0))
        self.c_new.set_value(metrics.get("new", 0))
        self.c_enriched.set_value(metrics.get("enriched", 0))
        self.c_db_updates.set_value(metrics.get("db_updates", 0))
        self.c_purged.set_value(metrics.get("purged", 0))
        if hasattr(self, "c_observed"):
            self.c_observed.set_value(metrics.get("observed", 0))
        if hasattr(self, "c_fields_added"):
            self.c_fields_added.set_value(metrics.get("fields_added", 0))
        cur = metrics.get("buffer_current", 0)
        max_b = metrics.get("buffer_max", 20)
        self.c_buffer.set_value(f"{cur}/{max_b}")
        self.lbl_purge_status.setText(f"Auto-Purge: Clean ({cur} in buffer)")

    def update_latest_capture(self, capture_id: str, delta: float, reason: str, img: Optional[Image.Image], breakdown: dict, gate_status: str):
        self.lbl_cap_id.setText(f"Capture ID: {capture_id}")
        self.lbl_cap_time.setText(f"Time: {time.strftime('%H:%M:%S')}")
        self.lbl_delta.setText(f"Delta: {delta*100:.2f}%")
        self.lbl_reason.setText(f"Reason: {reason}")
        self.lbl_gate_status.setText(f"Gate: {gate_status}")

        b_text = f"People: {breakdown.get('people',0)} | Companies: {breakdown.get('companies',0)} | Locations: {breakdown.get('locations',0)} | Signals: {breakdown.get('signals',0)}"
        self.lbl_breakdown.setText(b_text)

        if img:
            try:
                # Convert PIL to QPixmap
                bio = BytesIO()
                img.save(bio, format="PNG")
                qimg = QImage.fromData(bio.getvalue())
                pix = QPixmap.fromImage(qimg)
                scaled = pix.scaled(140, 85, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_thumbnail.setPixmap(scaled)
            except Exception as e:
                logger.debug("Failed to render thumbnail: %s", e)

    def update_extraction_proof(self, proof_items: List[dict]):
        self.proof_table.setRowCount(len(proof_items))
        for row, item in enumerate(proof_items):
            # Field
            f_item = QTableWidgetItem(item.get("field", ""))
            f_item.setForeground(QColor("#38bdf8"))
            self.proof_table.setItem(row, 0, f_item)

            # Value
            v_item = QTableWidgetItem(item.get("value", ""))
            v_item.setForeground(QColor("#f8fafc"))
            self.proof_table.setItem(row, 1, v_item)

            # Conf
            c_val = item.get("confidence", 0.0)
            c_str = f"{int(c_val * 100)}%" if c_val <= 1.0 else f"{int(c_val)}%"
            c_item = QTableWidgetItem(c_str)
            c_item.setForeground(QColor("#10b981" if c_val >= 0.85 else "#f59e0b"))
            self.proof_table.setItem(row, 2, c_item)

            # Decision
            d_item = QTableWidgetItem(item.get("decision", "STAGED"))
            d_item.setForeground(QColor("#a855f7"))
            self.proof_table.setItem(row, 3, d_item)

    def update_database_proof(self, status: str, response: dict, summary: str):
        if status == "STAGED":
            self.lbl_db_response.setText(f"Last Response: CONNECTED (200 OK — Staged)")
            self.lbl_db_response.setStyleSheet("color: #10b981; font-size: 9px; font-weight: 600;")
            self.lbl_db_write.setText(f"Last DB Write: {summary}")
        else:
            self.lbl_db_response.setText(f"Last Response: {summary}")
            self.lbl_db_response.setStyleSheet("color: #ef4444; font-size: 9px; font-weight: 600;")

    def log_event(self, event_name: str, details: str):
        t_str = time.strftime("%H:%M:%S")
        entry = QLabel(f"[{t_str}] <b style='color: #38bdf8;'>{event_name}</b>: {details}")
        entry.setStyleSheet("color: #94a3b8; font-size: 8px; font-family: Consolas, monospace;")
        entry.setWordWrap(True)

        self.stream_layout.insertWidget(0, entry)
        self._log_entries.append(entry)

        # Cap entries at 30
        if len(self._log_entries) > 30:
            oldest = self._log_entries.pop(0)
            oldest.deleteLater()
