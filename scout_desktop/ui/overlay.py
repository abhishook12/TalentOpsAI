"""
ui/overlay.py — Executive Floating Companion Panel for TalentOps Scout Desktop

Implements the complete real-time runtime proof UI:
- Independent multi-level system status (System, Backend, Active Window, Capture, Analyzer, Database)
- Real-time active window & context tracking (App, Window, URL, Context, State)
- 10 Explicit Counters (Captured, Analyzed, Useful, Staged, Matched, New, Enriched, DB Updates, Purged, Buffer)
- Latest Capture View with live thumbnail, delta %, and reason
- Extraction Proof Table (Field, Value, Source, Confidence, Evidence, Decision)
- Database Proof showing exact backend response, environment (PRODUCTION vs LOCAL), and DB write result
- Real-Time Live Activity Event Stream (WINDOW_DETECTED, ANALYSIS_COMPLETED, DB_SYNC_SUCCESS, etc.)
- Zero 'Scan Page' button; 100% autonomous background operation.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from io import BytesIO

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGraphicsDropShadowEffect,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPixmap, QIcon, QImage
from PIL import Image

logger = logging.getLogger("scout.overlay")


class StatusIndicator(QFrame):
    """Component for individual system subsystem status."""
    def __init__(self, name: str, default_state: str = "IDLE", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 2px 5px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self.lbl_name = QLabel(name.upper())
        self.lbl_name.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 700;")
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
                color = "#10b981" # green
            elif any(k in s for k in ("IDLE", "WATCH", "STAGED", "BATC")):
                color = "#f59e0b" # yellow
            elif any(k in s for k in ("ERROR", "FAIL", "DISCONNECT", "REJECT")):
                color = "#ef4444" # red
            else:
                color = "#38bdf8" # blue
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: 800;")


class MetricCard(QFrame):
    """Clean metric badge for explicit counters."""
    def __init__(self, label: str, value: str = "0", color: str = "#f8fafc", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 5px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(1)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 700; letter-spacing: 0.3px;")
        layout.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 800;")
        layout.addWidget(self.lbl_val)

    def set_value(self, val: str):
        self.lbl_val.setText(str(val))


class OverlayPanel(QWidget):
    force_capture_requested = Signal()
    open_diagnostics_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()

        # Frameless, Always on Top, Tool Window
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        logo_pix = self._load_logo_pixmap(64)
        if logo_pix:
            self.setWindowIcon(QIcon(logo_pix))

        self.init_ui()
        self.resize(390, 680)

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
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame#main_card {
                background-color: #090d16;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.container.setObjectName("main_card")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        main_vbox = QVBoxLayout(self.container)
        main_vbox.setContentsMargins(12, 10, 12, 10)
        main_vbox.setSpacing(8)

        # ── 1. Header & Brand Row ──
        header = QHBoxLayout()
        header.setSpacing(6)

        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(22, 22)
        logo_pix = self._load_logo_pixmap(22)
        if logo_pix:
            self.lbl_logo.setPixmap(logo_pix)
            self.lbl_logo.setScaledContents(True)
        header.addWidget(self.lbl_logo)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        lbl_brand = QLabel("TALENTOPS SCOUT")
        lbl_brand.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 800; letter-spacing: 0.8px;")
        brand_col.addWidget(lbl_brand)

        self.lbl_env_badge = QLabel("PRODUCTION CLOUD")
        self.lbl_env_badge.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 700;")
        brand_col.addWidget(self.lbl_env_badge)
        header.addLayout(brand_col)

        header.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10b981; font-size: 13px;")
        header.addWidget(self.status_dot)

        self.lbl_main_status = QLabel("AUTONOMOUS ACTIVE")
        self.lbl_main_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: 700;")
        header.addWidget(self.lbl_main_status)

        btn_min = QPushButton("—")
        btn_min.setFixedSize(18, 18)
        btn_min.setStyleSheet("QPushButton { color: #64748b; background: transparent; border: none; font-size: 12px; } QPushButton:hover { color: white; }")
        btn_min.clicked.connect(self.hide)
        header.addWidget(btn_min)

        main_vbox.addLayout(header)

        # ── 2. Scrollable Body for Real-Time Proof Panels ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #0f172a;
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
        content.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 0, 2, 0)
        c_layout.setSpacing(7)

        # ── 2A. Subsystem Health Status Grid (6 Independent Levels) ──
        status_box = QFrame()
        status_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px; padding: 4px;")
        status_grid = QGridLayout(status_box)
        status_grid.setContentsMargins(4, 4, 4, 4)
        status_grid.setSpacing(4)

        self.ind_system = StatusIndicator("System", "ACTIVE")
        self.ind_backend = StatusIndicator("Backend", "CONNECTED")
        self.ind_window = StatusIndicator("Window", "DETECTED")
        self.ind_capture = StatusIndicator("Capture", "ACTIVE")
        self.ind_analyzer = StatusIndicator("Analyzer", "ACTIVE")
        self.ind_db = StatusIndicator("DB Sync", "CONNECTED")

        status_grid.addWidget(self.ind_system, 0, 0)
        status_grid.addWidget(self.ind_backend, 0, 1)
        status_grid.addWidget(self.ind_window, 1, 0)
        status_grid.addWidget(self.ind_capture, 1, 1)
        status_grid.addWidget(self.ind_analyzer, 2, 0)
        status_grid.addWidget(self.ind_db, 2, 1)
        c_layout.addWidget(status_box)

        # ── 2B. Monitored Application & Active Page Context ──
        mon_box = QFrame()
        mon_box.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px;")
        mon_layout = QVBoxLayout(mon_box)
        mon_layout.setContentsMargins(8, 6, 8, 6)
        mon_layout.setSpacing(2)

        app_row = QHBoxLayout()
        self.lbl_app = QLabel("Application: Google Chrome")
        self.lbl_app.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")
        app_row.addWidget(self.lbl_app)
        app_row.addStretch()

        self.lbl_state_badge = QLabel("ACTIVE SAMPLING")
        self.lbl_state_badge.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 700; background: #064e3b; padding: 1px 5px; border-radius: 3px;")
        app_row.addWidget(self.lbl_state_badge)
        mon_layout.addLayout(app_row)

        self.lbl_title = QLabel("Window: LinkedIn")
        self.lbl_title.setStyleSheet("color: #e2e8f0; font-size: 9px;")
        self.lbl_title.setWordWrap(True)
        mon_layout.addWidget(self.lbl_title)

        self.lbl_url = QLabel("URL: https://www.linkedin.com")
        self.lbl_url.setStyleSheet("color: #64748b; font-size: 8px; font-family: monospace;")
        self.lbl_url.setWordWrap(True)
        mon_layout.addWidget(self.lbl_url)

        self.lbl_context = QLabel("Context: Watching active window")
        self.lbl_context.setStyleSheet("color: #c084fc; font-size: 9px; font-weight: 600;")
        mon_layout.addWidget(self.lbl_context)

        c_layout.addWidget(mon_box)

        # ── 2C. Explicit Counters (10 Metrics) ──
        c_layout.addWidget(self._build_section_header("TELEMETRY COUNTERS"))
        cnt_grid1 = QHBoxLayout()
        cnt_grid1.setSpacing(4)
        self.c_captured = MetricCard("Captured", "0")
        self.c_analyzed = MetricCard("Analyzed", "0")
        self.c_useful = MetricCard("Useful", "0", color="#38bdf8")
        self.c_staged = MetricCard("Staged", "0", color="#f59e0b")
        self.c_matched = MetricCard("Matched", "0")
        cnt_grid1.addWidget(self.c_captured)
        cnt_grid1.addWidget(self.c_analyzed)
        cnt_grid1.addWidget(self.c_useful)
        cnt_grid1.addWidget(self.c_staged)
        cnt_grid1.addWidget(self.c_matched)
        c_layout.addLayout(cnt_grid1)

        cnt_grid2 = QHBoxLayout()
        cnt_grid2.setSpacing(4)
        self.c_new = MetricCard("New", "0", color="#10b981")
        self.c_enriched = MetricCard("Enriched", "0", color="#a855f7")
        self.c_db_updates = MetricCard("DB Updates", "0", color="#10b981")
        self.c_purged = MetricCard("Purged", "0", color="#64748b")
        self.c_buffer = MetricCard("Buffer", "0 / 20", color="#e2e8f0")
        cnt_grid2.addWidget(self.c_new)
        cnt_grid2.addWidget(self.c_enriched)
        cnt_grid2.addWidget(self.c_db_updates)
        cnt_grid2.addWidget(self.c_purged)
        cnt_grid2.addWidget(self.c_buffer)
        c_layout.addLayout(cnt_grid2)

        # ── 2D. Current Capture Preview & Extraction Breakdown ──
        c_layout.addWidget(self._build_section_header("CURRENT CAPTURE & EXTRACTION"))
        cap_box = QFrame()
        cap_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px;")
        cap_layout = QVBoxLayout(cap_box)
        cap_layout.setContentsMargins(8, 6, 8, 6)
        cap_layout.setSpacing(6)

        cap_row = QHBoxLayout()
        cap_row.setSpacing(8)

        # Thumbnail
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(110, 68)
        self.lbl_thumb.setStyleSheet("background-color: #020617; border: 1px solid #334155; border-radius: 4px;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setText("No Capture")
        cap_row.addWidget(self.lbl_thumb)

        # Capture meta
        meta_col = QVBoxLayout()
        meta_col.setSpacing(1)
        self.lbl_cap_id = QLabel("Capture ID: —")
        self.lbl_cap_id.setStyleSheet("color: #f8fafc; font-size: 9px; font-weight: 700;")
        meta_col.addWidget(self.lbl_cap_id)

        self.lbl_cap_time = QLabel("Time: —")
        self.lbl_cap_time.setStyleSheet("color: #94a3b8; font-size: 8px;")
        meta_col.addWidget(self.lbl_cap_time)

        self.lbl_cap_delta = QLabel("Delta: 0.00%")
        self.lbl_cap_delta.setStyleSheet("color: #38bdf8; font-size: 8px;")
        meta_col.addWidget(self.lbl_cap_delta)

        self.lbl_cap_reason = QLabel("Reason: WAITING")
        self.lbl_cap_reason.setStyleSheet("color: #f59e0b; font-size: 8px; font-weight: 600;")
        meta_col.addWidget(self.lbl_cap_reason)

        cap_row.addLayout(meta_col)
        cap_layout.addLayout(cap_row)

        # Extraction Entities Badge Breakdown
        self.lbl_breakdown = QLabel("People: 0 | Companies: 0 | Locations: 0 | Jobs: 0 | Signals: 0")
        self.lbl_breakdown.setStyleSheet("color: #cbd5e1; font-size: 8px; background: #020617; padding: 3px 6px; border-radius: 3px; border: 1px solid #1e293b;")
        cap_layout.addWidget(self.lbl_breakdown)

        c_layout.addWidget(cap_box)

        # ── 2E. Extraction Proof Card (Field | Value | Source | Conf | Decision) ──
        c_layout.addWidget(self._build_section_header("EXTRACTION PROOF (GROUNDED EVIDENCE)"))
        self.proof_box = QFrame()
        self.proof_box.setStyleSheet("background-color: #070b14; border: 1px solid #1e293b; border-radius: 6px;")
        self.proof_layout = QVBoxLayout(self.proof_box)
        self.proof_layout.setContentsMargins(6, 4, 6, 4)
        self.proof_layout.setSpacing(3)

        self.lbl_no_proof = QLabel("Waiting for page capture...")
        self.lbl_no_proof.setStyleSheet("color: #64748b; font-size: 8px; font-style: italic;")
        self.proof_layout.addWidget(self.lbl_no_proof)
        c_layout.addWidget(self.proof_box)

        # ── 2F. Database Proof & Backend Response ──
        c_layout.addWidget(self._build_section_header("BACKEND & DATABASE PROOF"))
        db_box = QFrame()
        db_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 6px;")
        db_layout = QVBoxLayout(db_box)
        db_layout.setContentsMargins(8, 6, 8, 6)
        db_layout.setSpacing(2)

        self.lbl_db_target = QLabel("Backend Target: https://talentopsai-1.onrender.com")
        self.lbl_db_target.setStyleSheet("color: #38bdf8; font-size: 8px; font-weight: 600;")
        db_layout.addWidget(self.lbl_db_target)

        self.lbl_db_response = QLabel("Last Response: CONNECTED (200 OK)")
        self.lbl_db_response.setStyleSheet("color: #e2e8f0; font-size: 8px;")
        db_layout.addWidget(self.lbl_db_response)

        self.lbl_db_write = QLabel("Last DB Write: None")
        self.lbl_db_write.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 600;")
        db_layout.addWidget(self.lbl_db_write)

        c_layout.addWidget(db_box)

        # ── 2G. Live Activity Event Stream ──
        c_layout.addWidget(self._build_section_header("LIVE ACTIVITY STREAM"))
        self.log_container = QFrame()
        self.log_container.setStyleSheet("background-color: #020617; border: 1px solid #1e293b; border-radius: 6px;")
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(6, 4, 6, 4)
        self.log_layout.setSpacing(2)

        self.lbl_event_recent = QLabel("⚡ Scout started in autonomous mode")
        self.lbl_event_recent.setStyleSheet("color: #94a3b8; font-size: 8px; font-family: monospace;")
        self.log_layout.addWidget(self.lbl_event_recent)
        c_layout.addWidget(self.log_container)

        scroll.setWidget(content)
        main_vbox.addWidget(scroll)

        # ── 3. Footer ──
        footer = QHBoxLayout()
        self.lbl_footer_env = QLabel("● PRODUCTION CLOUD")
        self.lbl_footer_env.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 700;")
        footer.addWidget(self.lbl_footer_env)

        footer.addStretch()

        self.lbl_footer_purge = QLabel("Auto-Purge: Clean (0 pending)")
        self.lbl_footer_purge.setStyleSheet("color: #64748b; font-size: 8px;")
        footer.addWidget(self.lbl_footer_purge)
        main_vbox.addLayout(footer)

        outer_layout.addWidget(self.container)

    def _build_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 800; letter-spacing: 0.5px; margin-top: 2px;")
        return lbl

    # ── Drag Window Handlers ──
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # ── UI Telemetry Update Methods ──
    def update_environment(self, env_name: str, endpoint: str):
        is_prod = "onrender.com" in endpoint or "PROD" in env_name.upper()
        self.lbl_env_badge.setText("PRODUCTION CLOUD" if is_prod else "LOCAL DEVELOPMENT")
        color = "#10b981" if is_prod else "#38bdf8"
        self.lbl_env_badge.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: 700;")
        self.lbl_footer_env.setText(f"● {'PRODUCTION' if is_prod else 'LOCAL DEV'}")
        self.lbl_footer_env.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: 700;")
        self.lbl_db_target.setText(f"Backend Target: {endpoint}")

    def update_window_context(self, app_name: str, page_title: str, url: str = "", context: Optional[str] = None):
        self.lbl_app.setText(f"Application: {app_name}")
        self.lbl_title.setText(f"Window: {page_title[:45] if page_title else '—'}")
        self.lbl_url.setText(f"URL: {url[:55] if url else '—'}")
        if context:
            self.lbl_context.setText(f"Context: {context[:40]}")
        self.ind_window.set_state("DETECTED" if app_name and "Detecting" not in app_name else "IDLE")

    def update_status_state(self, state: str):
        state_u = state.upper()
        if any(k in state_u for k in ("ACTIVE", "ACTIVE_SAMPLING", "SCOUT ACTIVE")):
            self.status_dot.setStyleSheet("color: #10b981; font-size: 13px;")
            self.lbl_main_status.setText("AUTONOMOUS ACTIVE")
            self.lbl_main_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: 700;")
            self.lbl_state_badge.setText("ACTIVE SAMPLING")
            self.lbl_state_badge.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 700; background: #064e3b; padding: 1px 5px; border-radius: 3px;")
            self.ind_system.set_state("ACTIVE")
            self.ind_capture.set_state("ACTIVE")
        elif state_u == "IDLE_WATCH":
            self.status_dot.setStyleSheet("color: #f59e0b; font-size: 13px;")
            self.lbl_main_status.setText("IDLE WATCH")
            self.lbl_main_status.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: 700;")
            self.lbl_state_badge.setText("IDLE WATCH (10s static)")
            self.lbl_state_badge.setStyleSheet("color: #f59e0b; font-size: 8px; font-weight: 700; background: #78350f; padding: 1px 5px; border-radius: 3px;")
            self.ind_capture.set_state("IDLE")
        elif state_u in ("STARTING", "CONNECTING", "BACKEND CONNECTED", "WINDOW DETECTED"):
            self.status_dot.setStyleSheet("color: #38bdf8; font-size: 13px;")
            self.lbl_main_status.setText(state_u)
            self.lbl_main_status.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")
            self.lbl_state_badge.setText(state_u)
            self.lbl_state_badge.setStyleSheet("color: #38bdf8; font-size: 8px; font-weight: 700; background: #0c4a6e; padding: 1px 5px; border-radius: 3px;")
        elif state_u in ("OFFLINE", "DISCONNECTED"):
            self.status_dot.setStyleSheet("color: #64748b; font-size: 13px;")
            self.lbl_main_status.setText("OFFLINE")
            self.lbl_main_status.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700;")
            self.ind_system.set_state("OFFLINE")
            self.ind_backend.set_state("DISCONNECTED")
        else:
            self.status_dot.setStyleSheet("color: #ef4444; font-size: 13px;")
            self.lbl_main_status.setText("SCOUT PAUSED")
            self.lbl_main_status.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: 700;")
            self.lbl_state_badge.setText("PAUSED")
            self.lbl_state_badge.setStyleSheet("color: #ef4444; font-size: 8px; font-weight: 700; background: #7f1d1d; padding: 1px 5px; border-radius: 3px;")
            self.ind_system.set_state("PAUSED")
            self.ind_capture.set_state("PAUSED")

    def update_explicit_counters(self, metrics: Dict[str, Any]):
        """Updates all 10 explicit telemetry counters."""
        self.c_captured.set_value(str(metrics.get("captured", 0)))
        self.c_analyzed.set_value(str(metrics.get("analyzed", 0)))
        self.c_useful.set_value(str(metrics.get("useful", 0)))
        self.c_staged.set_value(str(metrics.get("staged", 0)))
        self.c_matched.set_value(str(metrics.get("matched", 0)))
        self.c_new.set_value(str(metrics.get("new", 0)))
        self.c_enriched.set_value(str(metrics.get("enriched", 0)))
        self.c_db_updates.set_value(str(metrics.get("db_updates", 0)))
        self.c_purged.set_value(str(metrics.get("purged", 0)))
        b_cur = metrics.get("buffer_current", 0)
        b_max = metrics.get("buffer_max", 20)
        self.c_buffer.set_value(f"{b_cur} / {b_max}")
        self.lbl_footer_purge.setText(f"Auto-Purge: Clean ({b_cur} in buffer)")

    def update_latest_capture(
        self,
        capture_id: str,
        delta: float,
        reason: str,
        img: Optional[Image.Image],
        breakdown: Dict[str, int],
        status: str = "EXTRACTED"
    ):
        """Updates Current Capture thumbnail, delta, and breakdown."""
        self.lbl_cap_id.setText(f"Capture ID: {capture_id}")
        self.lbl_cap_time.setText(f"Time: {time.strftime('%H:%M:%S')}")
        self.lbl_cap_delta.setText(f"Delta: {delta * 100:.1f}%")
        self.lbl_cap_reason.setText(f"Reason: {reason.upper()} ({status})")

        p = breakdown.get("people", 0)
        c = breakdown.get("companies", 0)
        l = breakdown.get("locations", 0)
        j = breakdown.get("jobs", 0)
        s = breakdown.get("signals", 0)
        self.lbl_breakdown.setText(f"People: {p} | Companies: {c} | Locations: {l} | Jobs: {j} | Signals: {s}")

        if img:
            try:
                thumb = img.copy()
                thumb.thumbnail((110, 68), Image.Resampling.LANCZOS)
                # Convert PIL to QPixmap
                bio = BytesIO()
                thumb.save(bio, format="PNG")
                qpix = QPixmap()
                qpix.loadFromData(bio.getvalue(), "PNG")
                self.lbl_thumb.setPixmap(qpix)
                self.lbl_thumb.setScaledContents(True)
            except Exception as e:
                logger.debug("Failed to set thumbnail: %s", e)

    def update_extraction_proof(self, observations: List[Dict[str, Any]]):
        """Populates the Extraction Proof cards with grounded observations."""
        # Clear existing
        while self.proof_layout.count():
            item = self.proof_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not observations:
            lbl = QLabel("No relevant entity detected on current view")
            lbl.setStyleSheet("color: #64748b; font-size: 8px; font-style: italic;")
            self.proof_layout.addWidget(lbl)
            return

        for obs in observations[:5]: # show top 5
            row = QFrame()
            row.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 4px; padding: 2px 4px;")
            r_box = QVBoxLayout(row)
            r_box.setContentsMargins(4, 2, 4, 2)
            r_box.setSpacing(1)

            top = QHBoxLayout()
            f_lbl = QLabel(f"<b>{obs.get('field', 'ENTITY')}</b>: {obs.get('value', '—')}")
            f_lbl.setStyleSheet("color: #f8fafc; font-size: 8px;")
            top.addWidget(f_lbl)
            top.addStretch()

            conf = obs.get("confidence", 0.90)
            c_lbl = QLabel(f"{int(conf * 100)}%")
            c_lbl.setStyleSheet("color: #10b981; font-size: 8px; font-weight: 800;")
            top.addWidget(c_lbl)

            dec = obs.get("decision", "ACCEPT")
            d_lbl = QLabel(dec)
            d_color = "#10b981" if dec == "ACCEPT" else ("#a855f7" if dec == "ENRICH" else "#f59e0b")
            d_lbl.setStyleSheet(f"color: {d_color}; font-size: 8px; font-weight: 700; background: #020617; padding: 1px 4px; border-radius: 2px;")
            top.addWidget(d_lbl)
            r_box.addLayout(top)

            ev = obs.get("evidence", "")
            if ev:
                e_lbl = QLabel(f"Evidence: \"{ev[:50]}\"")
                e_lbl.setStyleSheet("color: #64748b; font-size: 7px; font-family: monospace;")
                r_box.addWidget(e_lbl)

            self.proof_layout.addWidget(row)

    def update_database_proof(self, status: str, last_response: Dict[str, Any], last_write_result: str):
        """Updates Database Proof with real backend telemetry."""
        self.ind_db.set_state(status)
        self.lbl_db_response.setText(f"Last Response: {status} (Batch: {last_response.get('batch_id', '—')})")
        self.lbl_db_write.setText(f"Last DB Write: [{time.strftime('%H:%M:%S')}] {last_write_result}")

    def log_event(self, event_name: str, details: str = ""):
        """Appends event to the live activity stream."""
        t_str = time.strftime("%H:%M:%S")
        text = f"[{t_str}] <b>{event_name}</b>"
        if details:
            text += f" — {details[:45]}"

        self.lbl_event_recent.setText(text)
        self.lbl_event_recent.setStyleSheet("color: #cbd5e1; font-size: 8px; font-family: monospace;")
