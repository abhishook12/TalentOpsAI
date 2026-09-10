"""
ui/main_window.py — Level 3 Full Windows Companion Application Window

Redesigned for TalentOps Scout:
- Minimalist Obsidian Palette (#0B0E14, #131722, #1E2433, #F8FAFC, #94A3B8, #10B981, #0284C7)
- 1-Click Operations: [⚡ Scan Screen Now], [⏸ Pause / ▶ Resume], [☁ Sync to Cloud]
- Plain-English Live Status Card: Clear description of what Scout is watching
- 4-Step Visual Pipeline Funnel: 1. Scanned -> 2. Profiles Found -> 3. Real Verified -> 4. Cloud Synced
- Latest Candidate Hero Card: Name, Title, Company, Location, Status pill
- Collapsible Technical Drawer: Deep telemetry counters, thumbnail preview, extraction table, and live logs
- 100% Backward Compatible with all app.py signals, slots, and properties.
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

try:
    from ..version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "2.7.0"


class SubsystemIndicator(QFrame):
    """Subsystem status badge with clean minimalist dark styling."""
    def __init__(self, name: str, default_state: str = "IDLE", parent=None):
        super().__init__(parent)
        self.setObjectName("subsystemBadge")
        self.setStyleSheet("""
            QFrame#subsystemBadge {
                background-color: #0E131F;
                border: 1px solid #1E2433;
                border-radius: 5px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.lbl_name = QLabel(name.upper())
        self.lbl_name.setStyleSheet("color: #64748B; font-size: 8px; font-weight: 700;")
        layout.addWidget(self.lbl_name)

        layout.addStretch()

        self.lbl_val = QLabel(default_state)
        self.lbl_val.setStyleSheet("color: #94A3B8; font-size: 8px; font-weight: 800;")
        layout.addWidget(self.lbl_val)

    def set_state(self, state: str, color: Optional[str] = None):
        self.lbl_val.setText(state.upper())
        if not color:
            s = state.upper()
            if any(k in s for k in ("ACTIVE", "CONNECTED", "DETECTED", "SUCCESS", "GROUNDED")):
                color = "#10B981"  # emerald
            elif any(k in s for k in ("IDLE", "WATCH", "STAGED", "BATC")):
                color = "#F59E0B"  # amber
            elif any(k in s for k in ("ERROR", "FAIL", "DISCONNECT", "REJECT")):
                color = "#EF4444"  # red
            elif "PAUSED" in s:
                color = "#6366F1"  # indigo
            else:
                color = "#0284C7"  # sky
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 8px; font-weight: 800;")


class MetricBadge(QFrame):
    """Clean metric card for explicit counters."""
    def __init__(self, label: str, value: str = "0", color: str = "#F8FAFC", parent=None):
        super().__init__(parent)
        self.setObjectName("metricBadge")
        self.setStyleSheet("""
            QFrame#metricBadge {
                background-color: #0E131F;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(1)

        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet("color: #64748B; font-size: 8px; font-weight: 700;")
        layout.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 800;")
        layout.addWidget(self.lbl_val)

    def set_value(self, val: str):
        self.lbl_val.setText(str(val))

    @property
    def value(self) -> str:
        return self.lbl_val.text()


class FunnelStepCard(QFrame):
    """Clean card representing one stage of the 4-step pipeline funnel."""
    def __init__(self, step_num: str, title: str, subtitle: str, count: str = "0", accent_color: str = "#0284C7", parent=None):
        super().__init__(parent)
        self.setObjectName("funnelCard")
        self.setStyleSheet(f"""
            QFrame#funnelCard {{
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        lbl_step = QLabel(f"STEP {step_num}")
        lbl_step.setStyleSheet(f"color: {accent_color}; font-size: 9px; font-weight: 800;")
        top_row.addWidget(lbl_step)
        top_row.addStretch()

        self.lbl_count = QLabel(count)
        self.lbl_count.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 900;")
        top_row.addWidget(self.lbl_count)
        layout.addLayout(top_row)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #E2E8F0; font-size: 11px; font-weight: 700;")
        layout.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setStyleSheet("color: #64748B; font-size: 9px; font-weight: 500;")
        layout.addWidget(self.lbl_subtitle)

    def set_count(self, count: str):
        self.lbl_count.setText(str(count))


class MainWindow(QMainWindow):
    """
    Level 3: Executive Desktop Companion Window for TalentOps Scout.
    Combines effortless 1-click controls, crystal-clear visual funnel,
    and collapsible deep technical telemetry.
    """
    force_capture_requested = Signal()
    open_diagnostics_requested = Signal()
    open_settings_requested = Signal()
    shutdown_requested = Signal()
    dock_to_edge_requested = Signal()
    toggle_pause_requested = Signal()
    sync_now_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_shutting_down = False
        self._is_paused = False
        self._technical_drawer_expanded = False

        self.setWindowTitle(f"TalentOps Scout v{CURRENT_VERSION} — Autonomous Companion")
        self.resize(520, 860)
        self.setMinimumSize(460, 680)

        # Set taskbar/window icon
        self._app_icon = self._load_app_icon()
        if self._app_icon and not self._app_icon.isNull():
            self.setWindowIcon(self._app_icon)

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_taskbar_icon()

    def _apply_win32_taskbar_icon(self):
        """Explicitly sets WM_SETICON on the Win32 window handle for Windows Taskbar & Alt-Tab."""
        try:
            import ctypes
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010

            candidate_icos = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.ico")),
                os.path.abspath(r"c:\TalentOpsAI\talentops.ico"),
            ]
            ico_path = next((p for p in candidate_icos if os.path.exists(p)), None)
            if ico_path:
                h_icon_big = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                h_icon_small = ctypes.windll.user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                hwnd = int(self.winId())
                if h_icon_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                if h_icon_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
        except Exception as e:
            logger.debug("Failed to set Win32 taskbar icon: %s", e)

    def _load_app_icon(self) -> QIcon:
        candidate_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.ico")),
            os.path.abspath(r"c:\TalentOpsAI\scout_desktop\assets\logo.ico"),
            os.path.abspath(r"c:\TalentOpsAI\talentops.ico"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")),
            os.path.abspath(r"c:\TalentOpsAI\talentops-logo.png"),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                icon = QIcon(p)
                if not icon.isNull():
                    return icon
        return QIcon()

    def _load_logo_pixmap(self, size: int = 24) -> Optional[QPixmap]:
        candidate_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.ico")),
            os.path.abspath(r"c:\TalentOpsAI\talentops.ico"),
            os.path.abspath(r"c:\TalentOpsAI\talentops-logo.png"),
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
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #0B0E14;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(14, 12, 14, 12)
        main_vbox.setSpacing(10)

        # ── 1. Top Brand, Environment & Window Controls Header ──
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(28, 28)
        logo_pix = self._load_logo_pixmap(28)
        if logo_pix:
            self.lbl_logo.setPixmap(logo_pix)
            self.lbl_logo.setScaledContents(True)
        header.addWidget(self.lbl_logo)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(6)
        lbl_brand = QLabel("TALENTOPS SCOUT")
        lbl_brand.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        brand_row.addWidget(lbl_brand)

        self.lbl_version_pill = QLabel(f"v{CURRENT_VERSION}")
        self.lbl_version_pill.setStyleSheet("""
            background: #1E293B;
            color: #38BDF8;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 9px;
            font-weight: 800;
        """)
        brand_row.addWidget(self.lbl_version_pill)
        brand_row.addStretch()
        brand_col.addLayout(brand_row)

        self.lbl_env_badge = QLabel(f"PRODUCTION CLOUD • v{CURRENT_VERSION} [STABLE]")
        self.lbl_env_badge.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 700;")
        brand_col.addWidget(self.lbl_env_badge)
        header.addLayout(brand_col)

        header.addStretch()

        # State Indicator Chip
        state_chip = QFrame()
        state_chip.setObjectName("stateChip")
        state_chip.setStyleSheet("""
            QFrame#stateChip {
                background: #131722;
                border: 1px solid #1E2433;
                border-radius: 12px;
            }
            QLabel { border: none; background: transparent; }
        """)
        chip_layout = QHBoxLayout(state_chip)
        chip_layout.setContentsMargins(8, 3, 8, 3)
        chip_layout.setSpacing(5)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #10B981; font-size: 10px;")
        chip_layout.addWidget(self.status_dot)

        self.lbl_main_status = QLabel("ACTIVE WATCH")
        self.lbl_main_status.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 800;")
        chip_layout.addWidget(self.lbl_main_status)
        header.addWidget(state_chip)

        header.addSpacing(6)

        # Window Controls
        top_ctrl = QHBoxLayout()
        top_ctrl.setSpacing(4)

        self.btn_top_min = QPushButton("–")
        self.btn_top_min.setToolTip("Minimize to Windows Taskbar")
        self.btn_top_min.setFixedSize(26, 24)
        self.btn_top_min.setStyleSheet("""
            QPushButton {
                background: #131722;
                color: #94A3B8;
                border: 1px solid #1E2433;
                border-radius: 5px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1E2433;
                color: #FFFFFF;
                border-color: #334155;
            }
        """)
        self.btn_top_min.clicked.connect(self.showMinimized)
        top_ctrl.addWidget(self.btn_top_min)

        self.btn_top_side = QPushButton("◧ Side")
        self.btn_top_side.setToolTip("Hide to Compact Screen Edge Handle")
        self.btn_top_side.setFixedHeight(24)
        self.btn_top_side.setStyleSheet("""
            QPushButton {
                background: #0E1A2E;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 5px;
                padding: 0 8px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #0284C7;
                color: #FFFFFF;
            }
        """)
        self.btn_top_side.clicked.connect(self._dock_to_side)
        top_ctrl.addWidget(self.btn_top_side)

        self.btn_top_close = QPushButton("✕")
        self.btn_top_close.setToolTip("Exit App Completely")
        self.btn_top_close.setFixedSize(26, 24)
        self.btn_top_close.setStyleSheet("""
            QPushButton {
                background: #200D12;
                color: #F87171;
                border: 1px solid #7F1D1D;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: #DC2626;
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        self.btn_top_close.clicked.connect(self.shutdown_requested.emit)
        top_ctrl.addWidget(self.btn_top_close)

        header.addLayout(top_ctrl)
        main_vbox.addLayout(header)

        # ── 2. Primary 1-Click Operations Action Bar ──
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        # 1-Click Scan Screen Button
        self.btn_scan_now = QPushButton("⚡ Scan Screen Now")
        self.btn_scan_now.setToolTip("Instantly trigger optical sampling on active window")
        self.btn_scan_now.setFixedHeight(36)
        self.btn_scan_now.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1);
                color: #FFFFFF;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 800;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #0284C7);
                border-color: #7DD3FC;
            }
            QPushButton:pressed {
                background: #075985;
            }
        """)
        self.btn_scan_now.clicked.connect(self.force_capture_requested.emit)
        action_bar.addWidget(self.btn_scan_now, 4)

        # 1-Click Pause / Resume Toggle Button
        self.btn_pause_toggle = QPushButton("⏸ Pause")
        self.btn_pause_toggle.setToolTip("Pause or resume continuous visual watch loop")
        self.btn_pause_toggle.setFixedHeight(36)
        self.btn_pause_toggle.setStyleSheet("""
            QPushButton {
                background: #131722;
                color: #E2E8F0;
                border: 1px solid #1E2433;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #1E2433;
                border-color: #334155;
                color: #FFFFFF;
            }
        """)
        self.btn_pause_toggle.clicked.connect(self._handle_pause_toggle)
        action_bar.addWidget(self.btn_pause_toggle, 3)

        # 1-Click Sync to Cloud Button
        self.btn_sync_now = QPushButton("☁ Sync to Cloud")
        self.btn_sync_now.setToolTip("Manually flush offline SQLite queue to cloud database")
        self.btn_sync_now.setFixedHeight(36)
        self.btn_sync_now.setStyleSheet("""
            QPushButton {
                background: #0F2520;
                color: #34D399;
                border: 1px solid #059669;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 800;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #059669;
                color: #FFFFFF;
                border-color: #10B981;
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)
        self.btn_sync_now.clicked.connect(self.sync_now_requested.emit)
        action_bar.addWidget(self.btn_sync_now, 3)

        main_vbox.addLayout(action_bar)

        # ── 3. Plain-English Live Activity Banner ──
        live_card = QFrame()
        live_card.setObjectName("liveCard")
        live_card.setStyleSheet("""
            QFrame#liveCard {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-left: 3px solid #0284C7;
                border-radius: 8px;
            }
            QLabel { border: none; background: transparent; }
        """)
        live_layout = QVBoxLayout(live_card)
        live_layout.setContentsMargins(12, 10, 12, 10)
        live_layout.setSpacing(4)

        banner_top = QHBoxLayout()
        self.lbl_banner_action = QLabel("WHAT SCOUT IS DOING RIGHT NOW")
        self.lbl_banner_action.setStyleSheet("color: #38BDF8; font-size: 9px; font-weight: 800;")
        banner_top.addWidget(self.lbl_banner_action)
        banner_top.addStretch()

        self.lbl_sampling_pulse = QLabel("● WATCHING (1.0s interval)")
        self.lbl_sampling_pulse.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 700;")
        banner_top.addWidget(self.lbl_sampling_pulse)
        live_layout.addLayout(banner_top)

        self.lbl_target_desc = QLabel("Watching Google Chrome — Candidate profile scanner active...")
        self.lbl_target_desc.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 600;")
        self.lbl_target_desc.setWordWrap(True)
        live_layout.addWidget(self.lbl_target_desc)

        self.lbl_target_url = QLabel("Target: https://www.linkedin.com")
        self.lbl_target_url.setStyleSheet("color: #64748B; font-size: 9px; font-family: Consolas, monospace;")
        self.lbl_target_url.setWordWrap(True)
        live_layout.addWidget(self.lbl_target_url)

        main_vbox.addWidget(live_card)

        # ── 4. 4-Step Pipeline Funnel ──
        main_vbox.addWidget(self._build_section_header("PIPELINE FUNNEL"))

        funnel_grid = QGridLayout()
        funnel_grid.setSpacing(6)

        self.funnel_step1 = FunnelStepCard("1", "Scanned Screens", "Visual changes analyzed", count="0", accent_color="#0284C7")
        self.funnel_step2 = FunnelStepCard("2", "Profiles Found", "Candidate cards detected", count="0", accent_color="#38BDF8")
        self.funnel_step3 = FunnelStepCard("3", "Real Verified", "Grounded & noise-filtered", count="0", accent_color="#A855F7")
        self.funnel_step4 = FunnelStepCard("4", "Cloud Synced", "Live in PostgreSQL DB", count="0", accent_color="#10B981")

        funnel_grid.addWidget(self.funnel_step1, 0, 0)
        funnel_grid.addWidget(self.funnel_step2, 0, 1)
        funnel_grid.addWidget(self.funnel_step3, 1, 0)
        funnel_grid.addWidget(self.funnel_step4, 1, 1)

        main_vbox.addLayout(funnel_grid)

        # ── 5. Latest Candidate Hero Card ──
        main_vbox.addWidget(self._build_section_header("LATEST EXTRACTED CANDIDATE"))

        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        self.hero_card.setStyleSheet("""
            QFrame#heroCard {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-left: 3px solid #10B981;
                border-radius: 8px;
            }
            QLabel { border: none; background: transparent; }
        """)
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(12, 10, 12, 10)
        hero_layout.setSpacing(4)

        hero_top = QHBoxLayout()
        self.lbl_hero_name = QLabel("Waiting for Candidate Profile...")
        self.lbl_hero_name.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 800;")
        hero_top.addWidget(self.lbl_hero_name)
        hero_top.addStretch()

        self.lbl_hero_pill = QLabel("IDLE")
        self.lbl_hero_pill.setStyleSheet("""
            background: #0E1A2E;
            color: #38BDF8;
            border: 1px solid #0284C7;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 8px;
            font-weight: 800;
        """)
        hero_top.addWidget(self.lbl_hero_pill)
        hero_layout.addLayout(hero_top)

        self.lbl_hero_title = QLabel("Browse candidate profiles on LinkedIn or Google Chrome to capture")
        self.lbl_hero_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        self.lbl_hero_title.setWordWrap(True)
        hero_layout.addWidget(self.lbl_hero_title)

        hero_sub = QHBoxLayout()
        self.lbl_hero_company = QLabel("Company: —")
        self.lbl_hero_company.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 500;")
        hero_sub.addWidget(self.lbl_hero_company)

        hero_sub.addSpacing(12)

        self.lbl_hero_location = QLabel("Location: —")
        self.lbl_hero_location.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 500;")
        hero_sub.addWidget(self.lbl_hero_location)
        hero_sub.addStretch()

        hero_layout.addLayout(hero_sub)

        # Live Copilot Intelligence Badge
        self.lbl_hero_copilot = QLabel("🔍 Live Copilot: Ready to query TalentOps central database")
        self.lbl_hero_copilot.setStyleSheet("""
            color: #38BDF8; font-size: 10px; font-weight: 700;
            background: rgba(14, 165, 233, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px; padding: 4px 8px; margin-top: 4px;
        """)
        self.lbl_hero_copilot.setWordWrap(True)
        hero_layout.addWidget(self.lbl_hero_copilot)

        main_vbox.addWidget(self.hero_card)

        # ── 6. Collapsible Technical Telemetry Drawer Toggle ──
        self.btn_toggle_drawer = QPushButton("▾ Show Deep Technical Telemetry & Evidence (12 Counters, OCR, Logs)")
        self.btn_toggle_drawer.setFixedHeight(28)
        self.btn_toggle_drawer.setStyleSheet("""
            QPushButton {
                background: #0E131F;
                color: #94A3B8;
                border: 1px solid #1E2433;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 700;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover {
                background: #131722;
                color: #F8FAFC;
                border-color: #334155;
            }
        """)
        self.btn_toggle_drawer.clicked.connect(self._toggle_technical_drawer)
        main_vbox.addWidget(self.btn_toggle_drawer)

        # ── 7. Technical Drawer Body (Scrollable & Collapsible) ──
        self.drawer_scroll = QScrollArea()
        self.drawer_scroll.setWidgetResizable(True)
        self.drawer_scroll.setFrameShape(QFrame.NoFrame)
        self.drawer_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #0B0E14;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #1E2433;
                min-height: 20px;
                border-radius: 3px;
            }
        """)
        self.drawer_scroll.setVisible(False)

        drawer_content = QWidget()
        d_layout = QVBoxLayout(drawer_content)
        d_layout.setContentsMargins(0, 4, 4, 4)
        d_layout.setSpacing(8)

        # 7A. Subsystem Health Chips
        status_box = QFrame()
        status_box.setObjectName("statusBox")
        status_box.setStyleSheet("""
            QFrame#statusBox {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel { border: none; background: transparent; }
        """)
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
        d_layout.addWidget(status_box)

        # 7B. Explicit Telemetry Counters (12 Metrics)
        d_layout.addWidget(self._build_section_header("EXPLICIT TELEMETRY COUNTERS"))
        cnt_row1 = QHBoxLayout()
        cnt_row1.setSpacing(4)
        self.c_captured = MetricBadge("Captured", "0")
        self.c_analyzed = MetricBadge("Analyzed", "0")
        self.c_useful = MetricBadge("Useful", "0", color="#38BDF8")
        self.c_staged = MetricBadge("Staged", "0", color="#F59E0B")
        self.c_matched = MetricBadge("Matched", "0")
        cnt_row1.addWidget(self.c_captured)
        cnt_row1.addWidget(self.c_analyzed)
        cnt_row1.addWidget(self.c_useful)
        cnt_row1.addWidget(self.c_staged)
        cnt_row1.addWidget(self.c_matched)
        d_layout.addLayout(cnt_row1)

        cnt_row2 = QHBoxLayout()
        cnt_row2.setSpacing(4)
        self.c_new = MetricBadge("New", "0", color="#10B981")
        self.c_enriched = MetricBadge("Enriched", "0", color="#A855F7")
        self.c_db_updates = MetricBadge("DB Updates", "0", color="#38BDF8")
        self.c_purged = MetricBadge("Purged", "0", color="#64748B")
        self.c_buffer = MetricBadge("Buffer", "0/20", color="#F59E0B")
        cnt_row2.addWidget(self.c_new)
        cnt_row2.addWidget(self.c_enriched)
        cnt_row2.addWidget(self.c_db_updates)
        cnt_row2.addWidget(self.c_purged)
        cnt_row2.addWidget(self.c_buffer)
        d_layout.addLayout(cnt_row2)

        cnt_row3 = QHBoxLayout()
        cnt_row3.setSpacing(4)
        self.c_observed = MetricBadge("Observed", "0", color="#06B6D4")
        self.c_fields_added = MetricBadge("Fields Added", "0", color="#22C55E")
        cnt_row3.addWidget(self.c_observed)
        cnt_row3.addWidget(self.c_fields_added)
        cnt_row3.addStretch()
        d_layout.addLayout(cnt_row3)

        # 7C. Latest Frame Preview & Classification
        d_layout.addWidget(self._build_section_header("LATEST CAPTURE & REASON"))
        cap_box = QFrame()
        cap_box.setObjectName("capBox")
        cap_box.setStyleSheet("""
            QFrame#capBox {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel { border: none; background: transparent; }
        """)
        cap_layout = QVBoxLayout(cap_box)
        cap_layout.setContentsMargins(8, 8, 8, 8)
        cap_layout.setSpacing(6)

        cap_header = QHBoxLayout()
        self.lbl_cap_id = QLabel("Capture ID: ---")
        self.lbl_cap_id.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: 700;")
        cap_header.addWidget(self.lbl_cap_id)
        cap_header.addStretch()

        self.lbl_cap_time = QLabel("Time: ---")
        self.lbl_cap_time.setStyleSheet("color: #64748B; font-size: 9px;")
        cap_header.addWidget(self.lbl_cap_time)
        cap_layout.addLayout(cap_header)

        thumb_row = QHBoxLayout()
        thumb_row.setSpacing(8)

        self.lbl_thumbnail = QLabel("No Capture")
        self.lbl_thumbnail.setFixedSize(140, 85)
        self.lbl_thumbnail.setStyleSheet("background-color: #0B0E14; border: 1px dashed #1E2433; border-radius: 4px; color: #475569; font-size: 9px;")
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        thumb_row.addWidget(self.lbl_thumbnail)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(3)
        self.lbl_delta = QLabel("Delta: 0.00%")
        self.lbl_delta.setStyleSheet("color: #F8FAFC; font-size: 9px; font-weight: 600;")
        meta_col.addWidget(self.lbl_delta)

        self.lbl_reason = QLabel("Reason: WAITING")
        self.lbl_reason.setStyleSheet("color: #F59E0B; font-size: 9px; font-weight: 600;")
        meta_col.addWidget(self.lbl_reason)

        self.lbl_breakdown = QLabel("People: 0 | Companies: 0 | Locations: 0 | Signals: 0")
        self.lbl_breakdown.setStyleSheet("color: #94A3B8; font-size: 8px;")
        meta_col.addWidget(self.lbl_breakdown)

        self.lbl_gate_status = QLabel("Gate: WAITING_FRAME")
        self.lbl_gate_status.setStyleSheet("color: #10B981; font-size: 8px; font-weight: 700;")
        meta_col.addWidget(self.lbl_gate_status)

        thumb_row.addLayout(meta_col)
        cap_layout.addLayout(thumb_row)
        d_layout.addWidget(cap_box)

        # 7D. Grounded Extraction Proof Table
        d_layout.addWidget(self._build_section_header("EXTRACTION PROOF (GROUNDED EVIDENCE)"))
        self.proof_table = QTableWidget()
        self.proof_table.setColumnCount(4)
        self.proof_table.setHorizontalHeaderLabels(["Field", "Extracted Value", "Conf", "Decision"])
        self.proof_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proof_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proof_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.proof_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.proof_table.verticalHeader().setVisible(False)
        self.proof_table.setMinimumHeight(130)
        self.proof_table.setStyleSheet("""
            QTableWidget {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 6px;
                color: #E2E8F0;
                font-size: 9px;
                gridline-color: #1E2433;
            }
            QHeaderView::section {
                background-color: #0E131F;
                color: #64748B;
                font-size: 8px;
                font-weight: 700;
                border: none;
                padding: 4px;
            }
            QTableWidget::item {
                padding: 3px 6px;
            }
        """)
        d_layout.addWidget(self.proof_table)

        # 7E. Backend & Cloud Database Proof
        d_layout.addWidget(self._build_section_header("BACKEND & DATABASE PROOF"))
        db_box = QFrame()
        db_box.setObjectName("dbBox")
        db_box.setStyleSheet("""
            QFrame#dbBox {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel { border: none; background: transparent; }
        """)
        db_layout = QVBoxLayout(db_box)
        db_layout.setContentsMargins(8, 6, 8, 6)
        db_layout.setSpacing(2)

        self.lbl_db_target = QLabel("Backend Target: https://talentopsai-1.onrender.com")
        self.lbl_db_target.setStyleSheet("color: #38BDF8; font-size: 9px; font-family: Consolas, monospace;")
        db_layout.addWidget(self.lbl_db_target)

        self.lbl_db_response = QLabel("Last Response: CONNECTED (200 OK)")
        self.lbl_db_response.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 600;")
        db_layout.addWidget(self.lbl_db_response)

        self.lbl_db_write = QLabel("Last DB Write: None")
        self.lbl_db_write.setStyleSheet("color: #E2E8F0; font-size: 9px;")
        db_layout.addWidget(self.lbl_db_write)
        d_layout.addWidget(db_box)

        # 7F. Rolling Live Activity Stream
        d_layout.addWidget(self._build_section_header("LIVE ACTIVITY STREAM"))
        self.stream_box = QFrame()
        self.stream_box.setObjectName("streamBox")
        self.stream_box.setStyleSheet("""
            QFrame#streamBox {
                background-color: #0E131F;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel { border: none; background: transparent; }
        """)
        self.stream_layout = QVBoxLayout(self.stream_box)
        self.stream_layout.setContentsMargins(6, 6, 6, 6)
        self.stream_layout.setSpacing(2)

        self._log_entries: List[QLabel] = []
        d_layout.addWidget(self.stream_box)

        # Technical Drawer Tools Footer
        tech_tools = QHBoxLayout()
        tech_tools.setSpacing(6)

        btn_diag = QPushButton("Diagnostics")
        btn_diag.setStyleSheet("""
            QPushButton {
                background: #131722;
                color: #94A3B8;
                border: 1px solid #1E2433;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #1E2433;
                color: #FFFFFF;
            }
        """)
        btn_diag.clicked.connect(self.open_diagnostics_requested.emit)
        tech_tools.addWidget(btn_diag)

        btn_settings = QPushButton("Settings")
        btn_settings.setStyleSheet("""
            QPushButton {
                background: #131722;
                color: #94A3B8;
                border: 1px solid #1E2433;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover {
                background: #1E2433;
                color: #FFFFFF;
            }
        """)
        btn_settings.clicked.connect(self.open_settings_requested.emit)
        tech_tools.addWidget(btn_settings)

        self.btn_dev_mode = QPushButton("Dev Mode: OFF")
        self.btn_dev_mode.setCheckable(True)
        self.btn_dev_mode.setStyleSheet("""
            QPushButton {
                background: #131722;
                color: #64748B;
                border: 1px solid #1E2433;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:checked {
                background: #0E7490;
                color: #22D3EE;
                border: 1px solid #0891B2;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1E2433;
                color: #FFFFFF;
            }
        """)
        self.btn_dev_mode.toggled.connect(self._toggle_dev_mode)
        tech_tools.addWidget(self.btn_dev_mode)

        tech_tools.addStretch()

        self.lbl_purge_status = QLabel("Auto-Purge: Clean")
        self.lbl_purge_status.setStyleSheet("color: #64748B; font-size: 8px;")
        tech_tools.addWidget(self.lbl_purge_status)

        d_layout.addLayout(tech_tools)

        self.drawer_scroll.setWidget(drawer_content)
        main_vbox.addWidget(self.drawer_scroll, 1)

        # ── 8. Bottom App Controls Bar ──
        ctrl_bar = QFrame()
        ctrl_bar.setObjectName("ctrlBar")
        ctrl_bar.setStyleSheet("""
            QFrame#ctrlBar {
                background: #131722;
                border: 1px solid #1E2433;
                border-radius: 6px;
            }
            QLabel { border: none; background: transparent; }
        """)
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)
        ctrl_layout.setSpacing(6)

        lbl_controls_title = QLabel("CONTROLS:")
        lbl_controls_title.setStyleSheet("color: #64748B; font-size: 8px; font-weight: 800;")
        ctrl_layout.addWidget(lbl_controls_title)

        self.btn_min_taskbar = QPushButton("– Minimize")
        self.btn_min_taskbar.setToolTip("Minimize companion window to standard Windows taskbar")
        self.btn_min_taskbar.setStyleSheet("""
            QPushButton {
                background: #0E131F;
                color: #CBD5E1;
                border: 1px solid #1E2433;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1E2433;
                color: #FFFFFF;
                border-color: #334155;
            }
        """)
        self.btn_min_taskbar.clicked.connect(self.showMinimized)
        ctrl_layout.addWidget(self.btn_min_taskbar)

        self.btn_dock_side = QPushButton("◧ Hide to Side Tab")
        self.btn_dock_side.setToolTip("Hide companion window and keep the small side handle visible on screen edge")
        self.btn_dock_side.setStyleSheet("""
            QPushButton {
                background: #0E1A2E;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #0284C7;
                color: #FFFFFF;
                border-color: #38BDF8;
            }
        """)
        self.btn_dock_side.clicked.connect(self._dock_to_side)
        ctrl_layout.addWidget(self.btn_dock_side)

        ctrl_layout.addStretch()

        self.btn_exit_app = QPushButton("✕ Exit App")
        self.btn_exit_app.setToolTip("Completely stop visual sampling, background workers, and close TalentOps Scout")
        self.btn_exit_app.setStyleSheet("""
            QPushButton {
                background: #200D12;
                color: #F87171;
                border: 1px solid #7F1D1D;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: #DC2626;
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        self.btn_exit_app.clicked.connect(self.shutdown_requested.emit)
        ctrl_layout.addWidget(self.btn_exit_app)

        main_vbox.addWidget(ctrl_bar)

        self.lbl_footer_status = QLabel(f"TalentOps Scout v{CURRENT_VERSION} • Production Cloud Connected • Auto-Sync Active")
        self.lbl_footer_status.setStyleSheet("color: #475569; font-size: 8px; font-weight: 600; padding: 2px 0;")
        self.lbl_footer_status.setAlignment(Qt.AlignCenter)
        main_vbox.addWidget(self.lbl_footer_status)

    def _build_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748B; font-size: 9px; font-weight: 800; margin-top: 4px;")
        return lbl

    def _handle_pause_toggle(self):
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.btn_pause_toggle.setText("▶ Resume")
            self.btn_pause_toggle.setStyleSheet("""
                QPushButton {
                    background: #1E1B4B;
                    color: #A5B4FC;
                    border: 1px solid #6366F1;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 800;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background: #6366F1;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_pause_toggle.setText("⏸ Pause")
            self.btn_pause_toggle.setStyleSheet("""
                QPushButton {
                    background: #131722;
                    color: #E2E8F0;
                    border: 1px solid #1E2433;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background: #1E2433;
                    border-color: #334155;
                    color: #FFFFFF;
                }
            """)
        self.toggle_pause_requested.emit()

    def _toggle_technical_drawer(self):
        self._technical_drawer_expanded = not self._technical_drawer_expanded
        self.drawer_scroll.setVisible(self._technical_drawer_expanded)
        if self._technical_drawer_expanded:
            self.btn_toggle_drawer.setText("▴ Hide Deep Technical Telemetry & Evidence")
        else:
            self.btn_toggle_drawer.setText("▾ Show Deep Technical Telemetry & Evidence (12 Counters, OCR, Logs)")

    def _toggle_dev_mode(self, enabled: bool):
        if enabled:
            self.btn_dev_mode.setText("Dev Mode: ON")
            self.stream_box.setVisible(True)
            self.proof_table.setVisible(True)
        else:
            self.btn_dev_mode.setText("Dev Mode: OFF")
            self.stream_box.setVisible(True)
            self.proof_table.setVisible(True)

    def _dock_to_side(self):
        self.dock_to_edge_requested.emit()
        self.hide()

    def closeEvent(self, event: QCloseEvent):
        if getattr(self, "_is_shutting_down", False):
            event.accept()
            return
        event.ignore()
        self._dock_to_side()

    def update_environment(self, env_name: str, api_base: str):
        self.lbl_env_badge.setText(env_name.upper())
        self.lbl_db_target.setText(f"Backend Target: {api_base}")

    def update_status_state(self, state: str):
        s = state.upper()
        self.lbl_main_status.setText(s)
        if "ACTIVE" in s or "CONNECTED" in s or "DETECTED" in s:
            col = "#10B981"
        elif "IDLE" in s or "STAGED" in s:
            col = "#F59E0B"
        elif "PAUSED" in s:
            col = "#6366F1"
        else:
            col = "#EF4444"
        self.status_dot.setStyleSheet(f"color: {col}; font-size: 10px;")
        self.lbl_main_status.setStyleSheet(f"color: {col}; font-size: 9px; font-weight: 800;")

    def update_window_context(self, app_name: str, window_title: str, url: str, context: str, is_allowed: bool = True, target_type: str = ""):
        clean_title = window_title[:45] if window_title else "Screen Active"
        if is_allowed:
            if target_type in ("CHROME_LINKEDIN", "LINKEDIN"):
                self.lbl_target_desc.setText(f"Watching LinkedIn — Talent Profile Active ({clean_title})")
                self.lbl_target_url.setText(f"Target: {url or 'https://www.linkedin.com'}")
                self.lbl_sampling_pulse.setText("● SCANNING LINKEDIN")
                self.lbl_sampling_pulse.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (LINKEDIN)")
                self.status_dot.setStyleSheet("color: #10B981; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 800;")
            elif target_type == "GITHUB":
                self.lbl_target_desc.setText(f"Watching GitHub — Developer Profile Active ({clean_title})")
                self.lbl_target_url.setText(f"Target: {url or 'https://github.com'}")
                self.lbl_sampling_pulse.setText("● SCANNING GITHUB")
                self.lbl_sampling_pulse.setStyleSheet("color: #A855F7; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (GITHUB)")
                self.status_dot.setStyleSheet("color: #A855F7; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #A855F7; font-size: 9px; font-weight: 800;")
            elif target_type.startswith("ATS_"):
                ats_name = target_type.split("ATS_")[-1]
                self.lbl_target_desc.setText(f"Watching ATS ({ats_name}) — Candidate Review ({clean_title})")
                self.lbl_target_url.setText(f"Target ATS: {url or 'Applicant Tracking System'}")
                self.lbl_sampling_pulse.setText(f"● SCANNING {ats_name}")
                self.lbl_sampling_pulse.setStyleSheet("color: #F59E0B; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText(f"ACTIVE ({ats_name})")
                self.status_dot.setStyleSheet("color: #F59E0B; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #F59E0B; font-size: 9px; font-weight: 800;")
            elif target_type in ("GOOGLE_CHAT", "CHAT"):
                self.lbl_target_desc.setText(f"Watching Google Chat — {clean_title}")
                self.lbl_target_url.setText(f"Target: Google Chat ({url or 'Workspace Chat'})")
                self.lbl_sampling_pulse.setText("● SCANNING CHAT")
                self.lbl_sampling_pulse.setStyleSheet("color: #3B82F6; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (GOOGLE CHAT)")
                self.status_dot.setStyleSheet("color: #3B82F6; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #3B82F6; font-size: 9px; font-weight: 800;")
            elif target_type == "TEAMS":
                self.lbl_target_desc.setText(f"Watching Microsoft Teams — {clean_title}")
                self.lbl_target_url.setText("Target: Microsoft Teams (Chat/Meeting/Channel)")
                self.lbl_sampling_pulse.setText("● SCANNING TEAMS")
                self.lbl_sampling_pulse.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (MS TEAMS)")
                self.status_dot.setStyleSheet("color: #10B981; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 800;")
            elif target_type == "SLACK":
                self.lbl_target_desc.setText(f"Watching Slack — {clean_title}")
                self.lbl_target_url.setText("Target: Slack Workplace Channels & Notes")
                self.lbl_sampling_pulse.setText("● SCANNING SLACK")
                self.lbl_sampling_pulse.setStyleSheet("color: #E01E5A; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (SLACK)")
                self.status_dot.setStyleSheet("color: #E01E5A; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #E01E5A; font-size: 9px; font-weight: 800;")
            elif target_type == "WHATSAPP":
                self.lbl_target_desc.setText(f"Watching WhatsApp — {clean_title}")
                self.lbl_target_url.setText("Target: WhatsApp Web Recruiter Chat")
                self.lbl_sampling_pulse.setText("● SCANNING WHATSAPP")
                self.lbl_sampling_pulse.setStyleSheet("color: #25D366; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (WHATSAPP)")
                self.status_dot.setStyleSheet("color: #25D366; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #25D366; font-size: 9px; font-weight: 800;")
            elif target_type == "TELEGRAM":
                self.lbl_target_desc.setText(f"Watching Telegram — {clean_title}")
                self.lbl_target_url.setText("Target: Telegram Talent Channels")
                self.lbl_sampling_pulse.setText("● SCANNING TELEGRAM")
                self.lbl_sampling_pulse.setStyleSheet("color: #229ED9; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (TELEGRAM)")
                self.status_dot.setStyleSheet("color: #229ED9; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #229ED9; font-size: 9px; font-weight: 800;")
            elif target_type in ("GMAIL", "OUTLOOK"):
                self.lbl_target_desc.setText(f"Watching {target_type} Inbox — {clean_title}")
                self.lbl_target_url.setText(f"Target: {target_type} Candidate Submissions")
                self.lbl_sampling_pulse.setText(f"● SCANNING {target_type}")
                self.lbl_sampling_pulse.setStyleSheet("color: #EA4335; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText(f"ACTIVE ({target_type})")
                self.status_dot.setStyleSheet("color: #EA4335; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #EA4335; font-size: 9px; font-weight: 800;")
            elif target_type == "PDF_RESUME":
                self.lbl_target_desc.setText(f"Analyzing PDF Resume — {clean_title}")
                self.lbl_target_url.setText("Target: Candidate CV / Resume Document")
                self.lbl_sampling_pulse.setText("● SCANNING RESUME")
                self.lbl_sampling_pulse.setStyleSheet("color: #F97316; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (RESUME OCR)")
                self.status_dot.setStyleSheet("color: #F97316; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #F97316; font-size: 9px; font-weight: 800;")
            elif target_type in ("STACKOVERFLOW", "KAGGLE", "DICE", "WELLFOUND"):
                self.lbl_target_desc.setText(f"Watching {target_type} Community — {clean_title}")
                self.lbl_target_url.setText(f"Target: {target_type} Candidate Portfolio")
                self.lbl_sampling_pulse.setText(f"● SCANNING {target_type}")
                self.lbl_sampling_pulse.setStyleSheet("color: #8B5CF6; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText(f"ACTIVE ({target_type})")
                self.status_dot.setStyleSheet("color: #8B5CF6; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #8B5CF6; font-size: 9px; font-weight: 800;")
            elif target_type == "ZOOMINFO":
                self.lbl_target_desc.setText(f"Watching ZoomInfo — {clean_title}")
                self.lbl_target_url.setText("Target: ZoomInfo / ZoomInfo Lite Contact Profile")
                self.lbl_sampling_pulse.setText("● SCANNING ZOOMINFO")
                self.lbl_sampling_pulse.setStyleSheet("color: #F43F5E; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (ZOOMINFO)")
                self.status_dot.setStyleSheet("color: #F43F5E; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #F43F5E; font-size: 9px; font-weight: 800;")
            elif target_type == "APOLLO":
                self.lbl_target_desc.setText(f"Watching Apollo.io — {clean_title}")
                self.lbl_target_url.setText("Target: Apollo Sourcing & Leads Directory")
                self.lbl_sampling_pulse.setText("● SCANNING APOLLO")
                self.lbl_sampling_pulse.setStyleSheet("color: #EAB308; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText("ACTIVE (APOLLO.IO)")
                self.status_dot.setStyleSheet("color: #EAB308; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #EAB308; font-size: 9px; font-weight: 800;")
            elif target_type.startswith("ATS_"):
                ats_name = target_type.replace("ATS_", "")
                self.lbl_target_desc.setText(f"Watching {ats_name} ATS — {clean_title}")
                self.lbl_target_url.setText(f"Target: {ats_name} Recruiter Workspace")
                self.lbl_sampling_pulse.setText(f"● SCANNING {ats_name}")
                self.lbl_sampling_pulse.setStyleSheet("color: #06B6D4; font-size: 9px; font-weight: 700;")
                self.lbl_main_status.setText(f"ACTIVE ({ats_name})")
                self.status_dot.setStyleSheet("color: #06B6D4; font-size: 10px;")
                self.lbl_main_status.setStyleSheet("color: #06B6D4; font-size: 9px; font-weight: 800;")
            else:
                self.lbl_target_desc.setText(f"Watching [{app_name}] — {clean_title}")
                self.lbl_target_url.setText(f"Target URL: {url or '---'}")
            self.ind_window.set_state("DETECTED")
        else:
            if "BROWSER" in target_type or "SEARCH" in target_type:
                self.lbl_target_desc.setText(f"Resting (Browser) — Page outside talent allowlist ('{clean_title}')")
                self.lbl_target_url.setText(f"Scanner ignores search engines & non-talent pages ({url or 'web content'})")
            else:
                self.lbl_target_desc.setText(f"Resting [{app_name}] — Outside target allowlist")
                self.lbl_target_url.setText("Scanner active on LinkedIn, ZoomInfo, Apollo, GitHub, ATS systems (Greenhouse/Lever/Ashby), Teams & Google Chat")
            
            self.lbl_sampling_pulse.setText("💤 RESTING (0% CPU)")
            self.lbl_sampling_pulse.setStyleSheet("color: #64748B; font-size: 9px; font-weight: 700;")
            self.lbl_main_status.setText("RESTING (NON-TARGET)")
            self.status_dot.setStyleSheet("color: #64748B; font-size: 10px;")
            self.lbl_main_status.setStyleSheet("color: #64748B; font-size: 9px; font-weight: 800;")
            self.ind_window.set_state("IDLE")

    def update_candidate_card(
        self,
        name: str,
        title: Optional[str],
        company: Optional[str],
        location: Optional[str],
        status: str = "CLOUD COMMITTED",
        copilot_info: Optional[dict] = None,
    ):
        """Updates the prominent Latest Candidate Hero Card with clean details and Live Copilot info."""
        try:
            from scout_desktop.extractor.title_normalizer import classify_title
            t_info = classify_title(title) if title else None
            display_title = t_info["canonical_title"] if t_info else (title or "Professional Profile")
            if t_info and t_info["legacy_seniority"] not in ("Specialist", ""):
                display_title += f" • {t_info['legacy_seniority']}"
        except Exception:
            display_title = title or "Professional Profile"

        self.lbl_hero_name.setText(name or "Candidate Profile Detected")
        self.lbl_hero_title.setText(display_title)
        self.lbl_hero_company.setText(f"Company: {company or '—'}")
        self.lbl_hero_location.setText(f"Location: {location or '—'}")
        self.lbl_hero_pill.setText(status.upper())
        if "COMMITTED" in status or "SYNC" in status or "DATABASE" in status:
            self.lbl_hero_pill.setStyleSheet("background: #0F2520; color: #34D399; border: 1px solid #059669; border-radius: 10px; padding: 2px 8px; font-size: 8px; font-weight: 800;")
        else:
            self.lbl_hero_pill.setStyleSheet("background: #0E1A2E; color: #38BDF8; border: 1px solid #0284C7; border-radius: 10px; padding: 2px 8px; font-size: 8px; font-weight: 800;")

        # Update Live Copilot status badge
        if copilot_info and copilot_info.get("found"):
            e_text = f" • Email: {copilot_info['email']}" if copilot_info.get("email") else " • Verified Record on file"
            t_score = f" (Trust: {copilot_info.get('trust_score', 90)}%)"
            self.lbl_hero_copilot.setText(f"🟢 IN TALENTOPS DATABASE{e_text}{t_score}")
            self.lbl_hero_copilot.setStyleSheet("""
                color: #34D399; font-size: 10px; font-weight: 700;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 6px; padding: 4px 8px; margin-top: 4px;
            """)
        elif copilot_info and not copilot_info.get("found"):
            self.lbl_hero_copilot.setText("✨ NEW CANDIDATE LEAD — Automatically staging & resolving identity to database")
            self.lbl_hero_copilot.setStyleSheet("""
                color: #C084FC; font-size: 10px; font-weight: 700;
                background: rgba(168, 85, 247, 0.12);
                border: 1px solid rgba(168, 85, 247, 0.35);
                border-radius: 6px; padding: 4px 8px; margin-top: 4px;
            """)

    def update_explicit_counters(self, metrics: Dict[str, Any]):
        # 1. Update Technical Drawer Counters
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

        # 2. Update 4-Step Pipeline Funnel
        scanned_count = metrics.get("analyzed", 0)
        self.funnel_step1.set_count(scanned_count)

        profiles_count = metrics.get("useful", 0)
        self.funnel_step2.set_count(profiles_count)

        verified_count = metrics.get("staged", 0)
        self.funnel_step3.set_count(verified_count)

        synced_count = metrics.get("db_updates", 0)
        self.funnel_step4.set_count(synced_count)

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
            f_item = QTableWidgetItem(item.get("field", ""))
            f_item.setForeground(QColor("#38BDF8"))
            self.proof_table.setItem(row, 0, f_item)

            v_item = QTableWidgetItem(item.get("value", ""))
            v_item.setForeground(QColor("#F8FAFC"))
            self.proof_table.setItem(row, 1, v_item)

            c_val = item.get("confidence", 0.0)
            c_str = f"{int(c_val * 100)}%" if c_val <= 1.0 else f"{int(c_val)}%"
            c_item = QTableWidgetItem(c_str)
            c_item.setForeground(QColor("#10B981" if c_val >= 0.85 else "#F59E0B"))
            self.proof_table.setItem(row, 2, c_item)

            d_item = QTableWidgetItem(item.get("decision", "STAGED"))
            d_item.setForeground(QColor("#A855F7"))
            self.proof_table.setItem(row, 3, d_item)

    def update_database_proof(self, status: str, response: dict, summary: str):
        if status == "STAGED":
            self.lbl_db_response.setText("Last Response: CONNECTED (200 OK — Staged)")
            self.lbl_db_response.setStyleSheet("color: #10B981; font-size: 9px; font-weight: 600;")
            self.lbl_db_write.setText(f"Last DB Write: {summary}")
        else:
            self.lbl_db_response.setText(f"Last Response: {summary}")
            self.lbl_db_response.setStyleSheet("color: #EF4444; font-size: 9px; font-weight: 600;")

    def log_event(self, event_name: str, details: str):
        t_str = time.strftime("%H:%M:%S")
        entry = QLabel(f"[{t_str}] <b style='color: #38BDF8;'>{event_name}</b>: {details}")
        entry.setStyleSheet("color: #94A3B8; font-size: 8px; font-family: Consolas, monospace;")
        entry.setWordWrap(True)
        self.stream_layout.insertWidget(0, entry)

    def closeEvent(self, event: QCloseEvent):
        """
        Standard Windows application behavior:
        Clicking [X] hides the companion window to the system tray & edge handle
        so autonomous monitoring continues uninterrupted in the background.
        Full shutdown requires right-clicking the tray icon and choosing 'Exit Scout'.
        """
        if self._is_shutting_down:
            event.accept()
        else:
            event.ignore()
            self.hide()
            self.dock_to_edge_requested.emit()
            logger.info("MainWindow hidden to system tray / edge dock. Autonomous Scout continues in background.")
