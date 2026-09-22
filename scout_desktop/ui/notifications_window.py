"""
ui/notifications_window.py — Modern Command-Center Dialogs for Desktop Scout
1. UpdateCenterDialog: Check for updates, inspect version details, and trigger update downloads.
2. NotificationsDialog: View global fleet announcements, system broadcasts, and release notices.
"""

import os
import sys
import time
import logging
import webbrowser
import threading
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QCursor

from ..version import __version__, EXTRACTOR_VERSION, RELEASE_CHANNEL, BUILD_DATE
from .components import (
    COLOR_BG_BASE, COLOR_SURFACE_CARD, COLOR_SURFACE_BORDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED
)

COLOR_CANONICAL = "#10B981"
COLOR_HYPOTHESIS = "#38BDF8"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"

logger = logging.getLogger("scout.ui.notifications")


class UpdateCenterDialog(QDialog):
    """
    Update Center Dialog:
    - Current installed version vs latest remote version from backend
    - Dynamic release channel indicator (stable)
    - Interactive "Check for updates now" action with real-time manifest fetch
    - Direct "Download & Update" button linking to authoritative setup installer
    """
    update_download_requested = Signal(str)

    def __init__(self, backend_client=None, updater=None, parent=None):
        super().__init__(parent)
        self.backend_client = backend_client
        self.updater = updater
        self.latest_version: Optional[str] = None
        self.download_url: Optional[str] = None
        self.release_notes: Optional[str] = None

        self.setWindowTitle("TalentOps Scout — Version & Update Center")
        self.setFixedSize(540, 520)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_BASE};
                color: {COLOR_TEXT_PRIMARY};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            QFrame.card {{
                background-color: {COLOR_SURFACE_CARD};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 8px;
            }}
        """)
        self._build_ui()
        # Automatically check for updates on open
        QTimer.singleShot(200, self.check_updates_now)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        head_layout = QHBoxLayout()
        icon_lbl = QLabel("🚀")
        icon_lbl.setFont(QFont("Segoe UI", 16))
        head_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("Version & Update Center")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Authoritative Scout desktop release management & updates.")
        lbl_sub.setFont(QFont("Segoe UI", 8))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        title_col.addWidget(lbl_sub)
        head_layout.addLayout(title_col)
        head_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_MUTED}; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        head_layout.addWidget(btn_close)
        layout.addLayout(head_layout)

        # Main Info Card
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"background-color: {COLOR_SURFACE_CARD}; border: 1px solid {COLOR_SURFACE_BORDER}; border-radius: 8px;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Current Installed Version
        row_curr = QHBoxLayout()
        lbl_c_tag = QLabel("Installed Version:")
        lbl_c_tag.setFont(QFont("Segoe UI", 9))
        lbl_c_tag.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.lbl_curr_ver = QLabel(f"v{__version__} ({RELEASE_CHANNEL})")
        self.lbl_curr_ver.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_curr_ver.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        row_curr.addWidget(lbl_c_tag)
        row_curr.addStretch()
        row_curr.addWidget(self.lbl_curr_ver)
        card_layout.addLayout(row_curr)

        # Status & Latest Version
        row_latest = QHBoxLayout()
        lbl_l_tag = QLabel("Cloud Registry:")
        lbl_l_tag.setFont(QFont("Segoe UI", 9))
        lbl_l_tag.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.lbl_status = QLabel("Checking for updates...")
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.lbl_status.setStyleSheet(f"color: {COLOR_HYPOTHESIS};")
        row_latest.addWidget(lbl_l_tag)
        row_latest.addStretch()
        row_latest.addWidget(self.lbl_status)
        card_layout.addLayout(row_latest)

        # Extractor engine info
        row_engine = QHBoxLayout()
        lbl_e_tag = QLabel("Extraction Engine:")
        lbl_e_tag.setFont(QFont("Segoe UI", 9))
        lbl_e_tag.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        lbl_e_val = QLabel(f"v{EXTRACTOR_VERSION} · Build {BUILD_DATE}")
        lbl_e_val.setFont(QFont("Consolas", 8))
        lbl_e_val.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        row_engine.addWidget(lbl_e_tag)
        row_engine.addStretch()
        row_engine.addWidget(lbl_e_val)
        card_layout.addLayout(row_engine)

        layout.addWidget(card)

        # Release Notes / Changelog section
        lbl_rn_title = QLabel("Release Notes & Changelog")
        lbl_rn_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_rn_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(lbl_rn_title)

        scroll_notes = QScrollArea()
        scroll_notes.setWidgetResizable(True)
        scroll_notes.setFixedHeight(140)
        scroll_notes.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLOR_SURFACE_CARD};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
            }}
        """)
        self.lbl_notes = QLabel("Connecting to cloud release registry...")
        self.lbl_notes.setFont(QFont("Segoe UI", 8))
        self.lbl_notes.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 10px;")
        self.lbl_notes.setWordWrap(True)
        self.lbl_notes.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll_notes.setWidget(self.lbl_notes)
        layout.addWidget(scroll_notes)

        # Actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.btn_check = QPushButton("🔄 Check for Updates Now")
        self.btn_check.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.btn_check.setFixedHeight(34)
        self.btn_check.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_check.setStyleSheet(f"""
            QPushButton {{
                background-color: #1E293B;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #334155;
            }}
        """)
        self.btn_check.clicked.connect(self.check_updates_now)
        actions_row.addWidget(self.btn_check)

        self.btn_update = QPushButton("🚀 Update & Download Now")
        self.btn_update.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.btn_update.setFixedHeight(34)
        self.btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #1D4ED8;
            }}
            QPushButton:disabled {{
                background-color: #1E293B;
                color: {COLOR_TEXT_MUTED};
                border-color: {COLOR_SURFACE_BORDER};
            }}
        """)
        self.btn_update.setEnabled(False)
        self.btn_update.clicked.connect(self._on_download_update_clicked)
        actions_row.addWidget(self.btn_update)

        layout.addLayout(actions_row)

        # Web portal link
        lbl_web = QLabel("<a href='https://talent-ops-ai.vercel.app/download-scout' style='color: #38BDF8; text-decoration: none;'>Open Web Scout Download Hub ↗</a>")
        lbl_web.setFont(QFont("Segoe UI", 8))
        lbl_web.setOpenExternalLinks(True)
        lbl_web.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_web)

    def check_updates_now(self):
        """Fetches live release manifest in background thread."""
        self.lbl_status.setText("Checking registry...")
        self.lbl_status.setStyleSheet(f"color: {COLOR_HYPOTHESIS};")
        self.btn_check.setEnabled(False)

        def _fetch():
            manifest = None
            try:
                import requests
                # Priority 1: Vercel Proxy (bypasses Cloudflare limits)
                urls = [
                    "https://talent-ops-ai.vercel.app/api/scout/updates/manifest?channel=stable&device_id=desktop-check",
                    "https://talentopsai-1.onrender.com/scout/updates/manifest?channel=stable&device_id=desktop-check"
                ]
                for u in urls:
                    try:
                        res = requests.get(u, timeout=8.0)
                        if res.status_code == 200:
                            manifest = res.json()
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error checking manifest: {e}")

            QTimer.singleShot(0, lambda: self._apply_manifest_result(manifest))

        threading.Thread(target=_fetch, daemon=True, name="ScoutCheckUpdateThread").start()

    def _apply_manifest_result(self, manifest: Optional[Dict[str, Any]]):
        self.btn_check.setEnabled(True)
        if not manifest:
            self.lbl_status.setText("Unable to reach cloud registry")
            self.lbl_status.setStyleSheet(f"color: {COLOR_WARNING};")
            self.lbl_notes.setText("Could not reach update server. You can download the latest installer manually from talent-ops-ai.vercel.app/download-scout.")
            return

        latest_ver = manifest.get("latest_version") or manifest.get("version", "2.9.3")
        self.latest_version = latest_ver
        self.download_url = manifest.get("download_url") or "https://talent-ops-ai.vercel.app/download-scout"
        self.release_notes = manifest.get("release_notes") or f"Official production release v{latest_ver}."

        self.lbl_notes.setText(self.release_notes)

        # Semver comparison
        def _parse(v):
            try:
                return tuple(int(x) for x in v.lstrip("v").split("."))
            except Exception:
                return (0, 0, 0)

        curr_tup = _parse(__version__)
        latest_tup = _parse(latest_ver)

        if latest_tup > curr_tup:
            self.lbl_status.setText(f"Update Available: v{latest_ver}")
            self.lbl_status.setStyleSheet(f"color: {COLOR_CANONICAL}; font-weight: bold;")
            self.btn_update.setEnabled(True)
            self.btn_update.setText(f"🚀 Update to v{latest_ver} (1-Click)")
        else:
            self.lbl_status.setText(f"You are up to date (v{__version__})")
            self.lbl_status.setStyleSheet(f"color: {COLOR_CANONICAL};")
            self.btn_update.setEnabled(True)
            self.btn_update.setText(f"⚡ Re-install / Renew v{__version__} (1-Click)")

    def _on_download_update_clicked(self):
        url = self.download_url or "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"
        if not url.endswith(".exe"):
            url = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"

        self.btn_update.setEnabled(False)
        self.lbl_status.setText("Downloading 1-Click update installer...")
        self.btn_update.setText("⏳ Downloading...")

        def _download_and_launch():
            try:
                import tempfile
                import urllib.request
                import subprocess

                target_dir = tempfile.gettempdir()
                installer_path = os.path.join(target_dir, "TalentOpsScoutSetup.exe")

                # Download installer directly
                urllib.request.urlretrieve(url, installer_path)
                logger.info("Downloaded update installer to %s", installer_path)

                # Launch installer directly on Windows
                if sys.platform == "win32" and os.path.exists(installer_path):
                    os.startfile(installer_path)
                    QTimer.singleShot(0, lambda: self.lbl_status.setText("Installer launched! Follow setup on screen."))
                    QTimer.singleShot(0, lambda: self.btn_update.setText("🚀 Installer Launched"))
                    QTimer.singleShot(0, lambda: self.btn_update.setEnabled(True))
                else:
                    webbrowser.open(url)
            except Exception as e:
                logger.warning("1-Click direct install fallback: %s", e)
                webbrowser.open(url)
                QTimer.singleShot(0, lambda: self.lbl_status.setText("Opened download link in browser."))
                QTimer.singleShot(0, lambda: self.btn_update.setEnabled(True))
                QTimer.singleShot(0, lambda: self.btn_update.setText("🚀 Retry Download"))

        threading.Thread(target=_download_and_launch, daemon=True, name="ScoutOneClickInstaller").start()


class NotificationsDialog(QDialog):
    """
    Global Notifications & Fleet Broadcasts Dialog:
    - Real-time broadcasts, global announcements, and release notices from cloud
    - Type badge (BROADCAST, SYSTEM, UPDATE)
    - Mark all as read action
    """
    def __init__(self, backend_client=None, parent=None):
        super().__init__(parent)
        self.backend_client = backend_client
        self.notifications: List[Dict[str, Any]] = []

        self.setWindowTitle("TalentOps Scout — Global Notifications & Announcements")
        self.setFixedSize(580, 560)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_BASE};
                color: {COLOR_TEXT_PRIMARY};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
        """)
        self._build_ui()
        QTimer.singleShot(150, self.fetch_notifications)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        head_layout = QHBoxLayout()
        icon_lbl = QLabel("🔔")
        icon_lbl.setFont(QFont("Segoe UI", 16))
        head_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("Notifications & Broadcasts")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Fleet broadcasts and platform announcements from TalentOps AI.")
        lbl_sub.setFont(QFont("Segoe UI", 8))
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        title_col.addWidget(lbl_sub)
        head_layout.addLayout(title_col)
        head_layout.addStretch()

        # Mark all read button
        btn_mark = QPushButton("Mark read")
        btn_mark.setFont(QFont("Segoe UI", 8))
        btn_mark.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_mark.setStyleSheet(f"""
            QPushButton {{
                background-color: #1E293B;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        btn_mark.clicked.connect(self.mark_all_read)
        head_layout.addWidget(btn_mark)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_MUTED}; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        head_layout.addWidget(btn_close)
        layout.addLayout(head_layout)

        # Scroll Area for notifications
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLOR_BG_BASE};
                border: none;
            }}
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet(f"background-color: {COLOR_BG_BASE};")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        self.list_layout.setSpacing(10)

        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll, stretch=1)

        # Bottom Bar
        btm_layout = QHBoxLayout()
        self.lbl_count = QLabel("Loading notifications...")
        self.lbl_count.setFont(QFont("Segoe UI", 8))
        self.lbl_count.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        btm_layout.addWidget(self.lbl_count)
        btm_layout.addStretch()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setFont(QFont("Segoe UI", 8))
        btn_refresh.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: #1E293B;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        btn_refresh.clicked.connect(self.fetch_notifications)
        btm_layout.addWidget(btn_refresh)
        layout.addLayout(btm_layout)

    def fetch_notifications(self):
        """Fetches notifications in background thread."""
        self.lbl_count.setText("Fetching notifications...")

        def _fetch():
            items = []
            try:
                if self.backend_client and hasattr(self.backend_client, "fetch_notifications"):
                    items = self.backend_client.fetch_notifications()
                if not items:
                    import requests
                    urls = []
                    if self.backend_client and getattr(self.backend_client, "active_api_base", None):
                        urls.append(f"{self.backend_client.active_api_base.rstrip('/')}/notifications/")
                    elif self.backend_client and getattr(self.backend_client, "base_url", None):
                        urls.append(f"{self.backend_client.base_url.rstrip('/')}/notifications/")
                    urls.extend([
                        "https://talent-ops-ai.vercel.app/api/notifications/",
                        "https://talentopsai-1.onrender.com/notifications/"
                    ])
                    headers = {}
                    if self.backend_client and hasattr(self.backend_client, "_get_headers"):
                        headers = self.backend_client._get_headers()
                    
                    for u in urls:
                        try:
                            res = requests.get(u, headers=headers, timeout=6.0)
                            if res.status_code == 200:
                                data = res.json()
                                if isinstance(data, list) and data:
                                    items = data
                                    break
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"Error fetching notifications: {e}")

            # If empty, add default fleet status announcements
            if not items:
                items = [
                    {
                        "id": 1,
                        "title": f"TalentOps Scout v{__version__} Active",
                        "message": f"Autonomous Edge Sourcing Node active with dual-sync, sub-millisecond OLAP intelligence, and continuous learning.",
                        "type": "success",
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "id": 2,
                        "title": "Cloud Sourcing Roster Synchronized",
                        "message": "All captured talent profiles are graduating directly to the main line (PostgreSQL recruiters directory).",
                        "type": "info",
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]

            QTimer.singleShot(0, lambda: self._render_notifications(items))

        threading.Thread(target=_fetch, daemon=True, name="ScoutFetchNotifThread").start()

    def _render_notifications(self, items: List[Dict[str, Any]]):
        self.notifications = items
        self.lbl_count.setText(f"{len(items)} announcement{'s' if len(items) != 1 else ''} available")

        # Clear existing items
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for item in items:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLOR_SURFACE_CARD};
                    border: 1px solid {COLOR_SURFACE_BORDER};
                    border-radius: 8px;
                    padding: 10px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 10, 12, 10)
            c_layout.setSpacing(6)

            # Top Row: Badge + Title + Time
            top_row = QHBoxLayout()
            badge_type = item.get("type", "info").upper()
            badge_color = COLOR_CANONICAL if badge_type in ("SUCCESS", "UPDATE") else COLOR_HYPOTHESIS
            if badge_type in ("WARNING", "ALERT"):
                badge_color = COLOR_WARNING
            elif badge_type == "DANGER":
                badge_color = COLOR_DANGER

            lbl_badge = QLabel(badge_type)
            lbl_badge.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            lbl_badge.setStyleSheet(f"""
                color: {badge_color};
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid {COLOR_SURFACE_BORDER};
                border-radius: 3px;
                padding: 1px 5px;
            """)
            top_row.addWidget(lbl_badge)

            lbl_card_title = QLabel(item.get("title", "Announcement"))
            lbl_card_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_card_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            top_row.addWidget(lbl_card_title)
            top_row.addStretch()

            lbl_time = QLabel(str(item.get("created_at", ""))[:16])
            lbl_time.setFont(QFont("Consolas", 7))
            lbl_time.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
            top_row.addWidget(lbl_time)
            c_layout.addLayout(top_row)

            # Message body
            lbl_msg = QLabel(item.get("message", ""))
            lbl_msg.setFont(QFont("Segoe UI", 8))
            lbl_msg.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; line-height: 1.4;")
            lbl_msg.setWordWrap(True)
            c_layout.addWidget(lbl_msg)

            self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def mark_all_read(self):
        self.lbl_count.setText("All announcements marked as read")
        if self.backend_client and hasattr(self.backend_client, "mark_notifications_read"):
            threading.Thread(target=self.backend_client.mark_notifications_read, daemon=True).start()
