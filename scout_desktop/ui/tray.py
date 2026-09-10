"""
ui/tray.py — Native Windows System Tray Integration

Provides system tray presence, quick status glances, and background management.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtCore import Qt, Signal, QObject
import os
import logging

logger = logging.getLogger("scout.tray")

try:
    from ..version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "2.7.0"


def create_tray_icon_pixmap(status_color: str = "#10b981") -> QPixmap:
    """Draws a crisp system tray icon using the TalentOps logo with dynamic status badge."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # Base background rounded rect for high contrast on Windows dark/light taskbars
    painter.setBrush(QColor("#090d16"))
    painter.setPen(QColor("#1e293b"))
    painter.drawRoundedRect(1, 1, 30, 30, 7, 7)

    # Load and draw logo
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"),
        r"c:\TalentOpsAI\talentops-logo.png",
        r"c:\TalentOpsAI\frontend\public\talentops-logo.png",
    ]
    logo_drawn = False
    for p in candidate_paths:
        if os.path.exists(p):
            logo_pix = QPixmap(p)
            if not logo_pix.isNull():
                scaled_logo = logo_pix.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(5, 5, scaled_logo)
                logo_drawn = True
                break

    if not logo_drawn:
        painter.setPen(QColor("#f8fafc"))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, 32, 32, Qt.AlignCenter, "TO")

    # Dynamic status badge in bottom-right corner (diameter 9px with border)
    painter.setPen(QColor("#090d16"))
    painter.setBrush(QColor(status_color))
    painter.drawEllipse(21, 21, 9, 9)

    painter.end()
    return pixmap


class SystemTrayManager(QObject):
    show_overlay = Signal()
    show_diagnostics = Signal()
    show_settings = Signal()
    show_connection_status = Signal()
    force_capture = Signal()
    toggle_pause = Signal()
    request_pair_account = Signal()
    quit_app = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(parent)
        self.is_paused = False

        self.update_icon_status("ACTIVE")
        self._build_menu()
        self.tray.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
            }
        """)

        self.status_action = menu.addAction(f"● Scout v{CURRENT_VERSION}: Autonomous Active")
        self.status_action.setEnabled(False)
        menu.addSeparator()

        open_act = menu.addAction("Open Scout")
        open_act.triggered.connect(self.show_overlay.emit)

        self.pause_action = menu.addAction("Pause Scout")
        self.pause_action.triggered.connect(self._toggle_pause_action)

        force_capture_act = menu.addAction("⚡ Force Capture Now")
        force_capture_act.triggered.connect(self.force_capture.emit)

        menu.addSeparator()

        pair_act = menu.addAction("🔗 Connect Account / Pair Device...")
        pair_act.triggered.connect(self.request_pair_account.emit)

        diag_act = menu.addAction("Diagnostics")
        diag_act.triggered.connect(self.show_diagnostics.emit)

        settings_act = menu.addAction("Settings")
        settings_act.triggered.connect(self.show_settings.emit)

        conn_act = menu.addAction("Connection Status")
        conn_act.triggered.connect(self.show_connection_status.emit)

        menu.addSeparator()
        exit_act = menu.addAction("🛑 Exit All Operations (Full Shutdown)")
        exit_act.triggered.connect(self.quit_app.emit)

        self.tray.setContextMenu(menu)

    def _toggle_pause_action(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_action.setText("Resume Scout")
            self.update_icon_status("PAUSED")
        else:
            self.pause_action.setText("Pause Scout")
            self.update_icon_status("ACTIVE")
        self.toggle_pause.emit()

    def update_icon_status(self, state: str):
        """
        Updates tray icon color and tooltip based on state:
        GREEN:  AUTONOMOUS ACTIVE
        YELLOW: IDLE WATCH
        RED:    PAUSED / ERROR
        GRAY:   OFFLINE / DISCONNECTED
        """
        state_upper = state.upper()
        if state_upper in ["ACTIVE", "ACTIVE_SAMPLING"]:
            color = "#10b981"  # GREEN: AUTONOMOUS ACTIVE
            tip = f"TalentOps Scout v{CURRENT_VERSION}: AUTONOMOUS ACTIVE"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"● Scout v{CURRENT_VERSION}: Autonomous Active")
        elif state_upper == "IDLE_WATCH":
            color = "#f59e0b"  # YELLOW: IDLE WATCH
            tip = f"TalentOps Scout v{CURRENT_VERSION}: IDLE WATCH"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"🟡 Scout v{CURRENT_VERSION}: Idle Watch")
        elif state_upper in ["PAUSED", "STOPPED"]:
            color = "#3b82f6"  # BLUE: PAUSED by user
            tip = f"TalentOps Scout v{CURRENT_VERSION}: PAUSED"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"⏸ Scout v{CURRENT_VERSION}: Paused")
        elif state_upper in ["OFFLINE", "DISCONNECTED"]:
            color = "#64748b"  # GRAY: OFFLINE / DISCONNECTED
            tip = f"TalentOps Scout v{CURRENT_VERSION}: OFFLINE / DISCONNECTED"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"⚪ Scout v{CURRENT_VERSION}: Offline")
        elif state_upper in ["ERROR", "CAPTURE_ERROR"]:
            color = "#ef4444"  # RED: ERROR
            tip = f"TalentOps Scout v{CURRENT_VERSION}: ERROR"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"🔴 Scout v{CURRENT_VERSION}: Error")
        else:
            color = "#64748b"  # GRAY: unknown defaults to offline
            tip = f"TalentOps Scout v{CURRENT_VERSION}: {state}"
            if hasattr(self, "status_action"):
                self.status_action.setText(f"Scout v{CURRENT_VERSION}: {state}")

        pixmap = create_tray_icon_pixmap(color)
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip(tip)

    def show(self):
        self.tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_overlay.emit()
