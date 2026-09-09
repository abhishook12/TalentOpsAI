"""
ui/settings_window.py — Settings, Node Identity, Connection Status & Updates Window

Surface 4 of the TalentOps Scout Desktop architecture.
Provides configuration for:
- [✓] Start Scout with Windows (HKCU Run key)
- Node Identity (user_id, scout_id, device_id, session_id)
- Live Backend Connection Status & Heartbeat
- Telemetry & Staging Queue Management
- Autonomous Release Management & Channels (Stable, Beta, Internal)
"""

import os
import json
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QFrame, QTabWidget, QLineEdit, QMessageBox,
    QSpinBox, QComboBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor

from ..core.autostart import is_autostart_enabled, set_autostart_enabled
from ..core.updater import CURRENT_VERSION
from ..sync.backend_client import BackendClient
from ..sync.local_queue import LocalQueue


class SettingsWindow(QWidget):
    settings_saved = Signal()
    force_sync_requested = Signal()
    update_requested = Signal()

    def __init__(self, backend_client: BackendClient, local_queue: LocalQueue, auto_updater=None, parent=None):
        super().__init__(parent)
        self.backend = backend_client
        self.queue = local_queue
        self.updater = auto_updater

        self.setWindowTitle("TalentOps Scout — Settings & Fleet Telemetry")
        self.resize(600, 520)

        # Set Window Icon
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
        if not os.path.exists(logo_path):
            logo_path = r"c:\TalentOpsAI\talentops-logo.png"
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.setStyleSheet("""
            QWidget {
                background-color: #0b1120;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background: #0f172a;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #0b1120;
                color: #94a3b8;
                padding: 8px 18px;
                border: 1px solid #1e293b;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #0f172a;
                color: #38bdf8;
                border-color: #334155;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 12px;
                font-weight: 600;
                color: #f8fafc;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3b82f6;
                background: #1e293b;
            }
            QCheckBox::indicator:checked {
                background: #2563eb;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 6px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#secondary_btn {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
            }
            QPushButton#secondary_btn:hover {
                background-color: #334155;
                color: white;
            }
            QPushButton#danger_btn {
                background-color: #dc2626;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 700;
                border: none;
            }
            QPushButton#danger_btn:hover {
                background-color: #b91c1c;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_logo = QLabel()
        lbl_logo.setFixedSize(28, 28)
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
        header.addWidget(lbl_logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("TALENTOPS SCOUT DESKTOP")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 800; letter-spacing: 0.5px; color: #f8fafc;")
        title_box.addWidget(lbl_title)
        lbl_sub = QLabel("Autonomous Intelligence Companion Configuration & Fleet Telemetry")
        lbl_sub.setStyleSheet("font-size: 10px; color: #94a3b8;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)
        header.addStretch()

        main_layout.addLayout(header)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: General & Windows Behavior
        tab_general = QWidget()
        gen_layout = QVBoxLayout(tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(16)

        # Section: Windows Startup
        startup_box = QFrame()
        startup_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        sb_layout = QVBoxLayout(startup_box)
        sb_layout.setSpacing(6)

        self.chk_autostart = QCheckBox("Start Scout with Windows")
        self.chk_autostart.setChecked(is_autostart_enabled())
        self.chk_autostart.toggled.connect(self._on_autostart_toggled)
        sb_layout.addWidget(self.chk_autostart)

        lbl_auto_desc = QLabel("Launches the Scout companion quietly in the Windows system tray upon login.")
        lbl_auto_desc.setStyleSheet("color: #94a3b8; font-size: 10px; margin-left: 26px;")
        sb_layout.addWidget(lbl_auto_desc)
        gen_layout.addWidget(startup_box)

        # Section: Autonomous Sampling Rates
        rates_box = QFrame()
        rates_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        rb_layout = QVBoxLayout(rates_box)
        rb_layout.setSpacing(10)

        lbl_rates = QLabel("AUTONOMOUS ENGINE TUNING")
        lbl_rates.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 10px;")
        rb_layout.addWidget(lbl_rates)

        row_sample = QHBoxLayout()
        row_sample.addWidget(QLabel("Active Sampling Rate:"))
        self.spin_rate = QSpinBox()
        self.spin_rate.setRange(1, 10)
        self.spin_rate.setValue(1)
        self.spin_rate.setSuffix(" sec")
        row_sample.addWidget(self.spin_rate)
        rb_layout.addLayout(row_sample)

        row_idle = QHBoxLayout()
        row_idle.addWidget(QLabel("10-Second Idle Rule Transition:"))
        self.spin_idle = QSpinBox()
        self.spin_idle.setRange(5, 60)
        self.spin_idle.setValue(10)
        self.spin_idle.setSuffix(" sec")
        row_idle.addWidget(self.spin_idle)
        rb_layout.addLayout(row_idle)

        row_ttl = QHBoxLayout()
        row_ttl.addWidget(QLabel("Screenshot Retention (Audit TTL):"))
        self.spin_ttl = QSpinBox()
        self.spin_ttl.setRange(15, 180)
        self.spin_ttl.setValue(30)
        self.spin_ttl.setSuffix(" sec")
        row_ttl.addWidget(self.spin_ttl)
        rb_layout.addLayout(row_ttl)

        gen_layout.addWidget(rates_box)
        gen_layout.addStretch()
        tabs.addTab(tab_general, "General")

        # Tab 2: Node Identity
        tab_identity = QWidget()
        id_layout = QVBoxLayout(tab_identity)
        id_layout.setContentsMargins(16, 16, 16, 16)
        id_layout.setSpacing(12)

        lbl_sec_warn = QLabel("🔒 Client Security Policy: Zero Database Secrets")
        lbl_sec_warn.setStyleSheet("color: #10b981; font-weight: 700; font-size: 11px;")
        id_layout.addWidget(lbl_sec_warn)

        lbl_sec_desc = QLabel(
            "This desktop companion never stores database credentials or master passwords. "
            "All synchronization routes through authenticated backend staging and identity resolution."
        )
        lbl_sec_desc.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lbl_sec_desc.setWordWrap(True)
        id_layout.addWidget(lbl_sec_desc)

        cfg_box = QFrame()
        cfg_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        cb_layout = QVBoxLayout(cfg_box)
        cb_layout.setSpacing(8)

        # Fields
        for name, val in [
            ("User ID:", str(self.backend.user_id)),
            ("Device ID:", self.backend.device_id),
            ("Scout Node ID:", f"SCOUT-{self.backend.device_id[:8].upper()}"),
            ("Active Session ID:", self.backend.session_id),
        ]:
            r = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #cbd5e1; font-weight: 600; min-width: 110px;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet("color: #38bdf8; font-family: monospace;")
            val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            r.addWidget(lbl)
            r.addWidget(val_lbl)
            r.addStretch()
            cb_layout.addLayout(r)

        id_layout.addWidget(cfg_box)
        id_layout.addStretch()
        tabs.addTab(tab_identity, "Node Identity")

        # Tab 3: Connection & Health Status
        tab_conn = QWidget()
        conn_layout = QVBoxLayout(tab_conn)
        conn_layout.setContentsMargins(16, 16, 16, 16)
        conn_layout.setSpacing(12)

        c_box = QFrame()
        c_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        c_layout = QVBoxLayout(c_box)
        c_layout.setSpacing(8)

        self.lbl_conn_status = QLabel("● Status: Checking...")
        self.lbl_conn_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        c_layout.addWidget(self.lbl_conn_status)

        self.lbl_endpoint = QLabel(f"Endpoint: {self.backend.base_url}")
        self.lbl_endpoint.setStyleSheet("color: #94a3b8; font-family: monospace;")
        c_layout.addWidget(self.lbl_endpoint)

        self.lbl_hb = QLabel("Heartbeat Interval: 30s")
        self.lbl_hb.setStyleSheet("color: #94a3b8;")
        c_layout.addWidget(self.lbl_hb)

        btn_test_conn = QPushButton("Ping Backend Now")
        btn_test_conn.setObjectName("secondary_btn")
        btn_test_conn.clicked.connect(self.test_connection)
        c_layout.addWidget(btn_test_conn)

        conn_layout.addWidget(c_box)

        # Queue box
        q_box = QFrame()
        q_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        q_layout = QVBoxLayout(q_box)
        q_layout.setSpacing(8)

        lbl_q_title = QLabel("LOCAL OFFLINE STAGING QUEUE (SQLite)")
        lbl_q_title.setStyleSheet("font-weight: 700; color: #a855f7; font-size: 10px;")
        q_layout.addWidget(lbl_q_title)

        stats = self.queue.get_queue_stats()
        self.lbl_q_stats = QLabel(f"Pending: {stats['pending']} | Synced Today: {stats['synced_today']} | Total: {stats['total']}")
        self.lbl_q_stats.setStyleSheet("color: #f8fafc; font-family: monospace;")
        q_layout.addWidget(self.lbl_q_stats)

        btn_sync = QPushButton("Sync Staging Queue Now")
        btn_sync.clicked.connect(self._on_sync_clicked)
        q_layout.addWidget(btn_sync)

        conn_layout.addWidget(q_box)
        conn_layout.addStretch()
        tabs.addTab(tab_conn, "Connection Status")

        # Tab 4: Updates & Releases
        tab_updates = QWidget()
        up_layout = QVBoxLayout(tab_updates)
        up_layout.setContentsMargins(16, 16, 16, 16)
        up_layout.setSpacing(12)

        # Release Info Box
        u_box = QFrame()
        u_box.setStyleSheet("background-color: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 12px;")
        ub_layout = QVBoxLayout(u_box)
        ub_layout.setSpacing(10)

        row_v = QHBoxLayout()
        v_title = QLabel("Scout Version:")
        v_title.setStyleSheet("font-weight: 700; color: #cbd5e1; font-size: 12px;")
        self.lbl_ver_val = QLabel(f"v{CURRENT_VERSION}")
        self.lbl_ver_val.setStyleSheet("font-weight: 800; color: #f8fafc; font-size: 13px; margin-left: 4px;")
        self.lbl_ver_badge = QLabel("✓ Up to date")
        self.lbl_ver_badge.setStyleSheet("color: #10b981; background-color: rgba(16, 185, 129, 0.15); border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px;")
        row_v.addWidget(v_title)
        row_v.addWidget(self.lbl_ver_val)
        row_v.addWidget(self.lbl_ver_badge)
        row_v.addStretch()
        ub_layout.addLayout(row_v)

        # Channel Selector
        row_ch = QHBoxLayout()
        lbl_ch = QLabel("Update Channel:")
        lbl_ch.setStyleSheet("color: #94a3b8; font-weight: 600;")
        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["Stable", "Beta", "Internal"])
        cur_ch = (self.updater.channel if self.updater else "stable").capitalize()
        idx = self.combo_channel.findText(cur_ch)
        if idx >= 0:
            self.combo_channel.setCurrentIndex(idx)
        self.combo_channel.currentTextChanged.connect(self._on_channel_changed)
        row_ch.addWidget(lbl_ch)
        row_ch.addWidget(self.combo_channel)
        row_ch.addStretch()
        ub_layout.addLayout(row_ch)

        # Auto-update options
        self.chk_auto_download = QCheckBox("Download updates automatically in background")
        self.chk_auto_download.setChecked(True)
        ub_layout.addWidget(self.chk_auto_download)

        self.chk_auto_restart = QCheckBox("Restart companion automatically after silent update")
        self.chk_auto_restart.setChecked(True)
        ub_layout.addWidget(self.chk_auto_restart)

        # Check button & timestamp
        row_check = QHBoxLayout()
        btn_check = QPushButton("Check for Updates")
        btn_check.clicked.connect(self._on_check_updates_clicked)
        self.lbl_last_check = QLabel(f"Last checked: {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
        self.lbl_last_check.setStyleSheet("color: #94a3b8; font-size: 10px;")
        row_check.addWidget(btn_check)
        row_check.addWidget(self.lbl_last_check)
        row_check.addStretch()
        ub_layout.addLayout(row_check)

        up_layout.addWidget(u_box)

        # Card: New Version Available (Dynamic)
        self.card_update = QFrame()
        self.card_update.setStyleSheet("background-color: #0c1a30; border: 1px solid #38bdf8; border-radius: 8px; padding: 12px;")
        cu_layout = QVBoxLayout(self.card_update)
        cu_layout.setSpacing(6)
        self.lbl_update_title = QLabel("New version available: Scout v2.1.0")
        self.lbl_update_title.setStyleSheet("font-weight: 800; color: #38bdf8; font-size: 12px;")
        cu_layout.addWidget(self.lbl_update_title)

        self.lbl_update_notes = QLabel("• Improved background screen sampling\n• Cryptographic trust chain & signature verification\n• Resilient SQLite schema migration runner")
        self.lbl_update_notes.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        cu_layout.addWidget(self.lbl_update_notes)

        btn_update_now = QPushButton("Update Now")
        btn_update_now.clicked.connect(self._on_update_now_clicked)
        cu_layout.addWidget(btn_update_now)
        self.card_update.hide()  # Hidden until update found
        up_layout.addWidget(self.card_update)

        # Card: Mandatory Update Required (Dynamic)
        self.card_mandatory = QFrame()
        self.card_mandatory.setStyleSheet("background-color: #2b0d0d; border: 1px solid #ef4444; border-radius: 8px; padding: 12px;")
        cm_layout = QVBoxLayout(self.card_mandatory)
        cm_layout.setSpacing(6)
        lbl_mand_title = QLabel("⚠ Update Required — Your version is no longer supported")
        lbl_mand_title.setStyleSheet("font-weight: 800; color: #ef4444; font-size: 12px;")
        cm_layout.addWidget(lbl_mand_title)

        self.lbl_mand_desc = QLabel("Your client version is below the minimum required floor. Update is required to resume profile capture.")
        self.lbl_mand_desc.setStyleSheet("color: #fca5a5; font-size: 10px;")
        cm_layout.addWidget(self.lbl_mand_desc)

        btn_mand_update = QPushButton("Update Scout Now")
        btn_mand_update.setObjectName("danger_btn")
        btn_mand_update.clicked.connect(self._on_update_now_clicked)
        cm_layout.addWidget(btn_mand_update)
        self.card_mandatory.hide()  # Hidden until mandatory trigger
        up_layout.addWidget(self.card_mandatory)

        up_layout.addStretch()
        tabs.addTab(tab_updates, "Updates & Releases")

        main_layout.addWidget(tabs)

        # Bottom Action Bar with Save + Close
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_save = QPushButton("💾 Save Settings")
        btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(btn_save)

        btn_close = QPushButton("Close")
        btn_close.setObjectName("secondary_btn")
        btn_close.clicked.connect(self.hide)
        btn_box.addWidget(btn_close)

        main_layout.addLayout(btn_box)

        # Load saved config values into spinboxes
        self._load_config_into_ui()

        # Initial checks
        self.test_connection()
        if self.updater:
            self._sync_updater_ui()

    def _sync_updater_ui(self):
        """Synchronizes UI state with AutoUpdater model."""
        if not self.updater:
            return
        self.lbl_ver_val.setText(f"v{self.updater.current_version}")
        if self.updater.is_mandatory:
            self.lbl_ver_badge.setText("⚠ Update Required")
            self.lbl_ver_badge.setStyleSheet("color: #ef4444; background-color: rgba(239, 68, 68, 0.15); border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px;")
            self.card_mandatory.show()
            self.card_update.hide()
        elif self.updater.pending_version:
            self.lbl_ver_badge.setText(f"● Update Available (v{self.updater.pending_version})")
            self.lbl_ver_badge.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.15); border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px;")
            self.lbl_update_title.setText(f"New version available: Scout v{self.updater.pending_version}")
            if self.updater.release_notes:
                self.lbl_update_notes.setText(self.updater.release_notes)
            self.card_update.show()
            self.card_mandatory.hide()
        else:
            self.lbl_ver_badge.setText("✓ Up to date")
            self.lbl_ver_badge.setStyleSheet("color: #10b981; background-color: rgba(16, 185, 129, 0.15); border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px;")
            self.card_update.hide()
            self.card_mandatory.hide()

    def _on_check_updates_clicked(self):
        self.lbl_last_check.setText(f"Checking now...")
        if self.updater:
            manifest = self.updater.check_for_updates_now()
            self.lbl_last_check.setText(f"Last checked: {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
            self._sync_updater_ui()
            if not manifest:
                QMessageBox.warning(self, "Update Check", "Unable to contact update server or manifest signature was invalid.")
            elif not self.updater.pending_version and not self.updater.is_mandatory:
                QMessageBox.information(self, "Up to Date", f"TalentOps Scout v{CURRENT_VERSION} is currently up to date.")
        else:
            self.lbl_last_check.setText(f"Last checked: {datetime.now().strftime('%b %d, %Y %I:%M %p')}")
            QMessageBox.information(self, "Up to Date", f"TalentOps Scout v{CURRENT_VERSION} is currently up to date.")

    def _on_channel_changed(self, channel_name: str):
        ch = channel_name.lower()
        if self.updater:
            self.updater.channel = ch
            self._on_check_updates_clicked()

    def _on_update_now_clicked(self):
        if self.updater:
            if self.updater.downloaded_installer_path:
                self.updater.apply_update_and_restart()
            else:
                manifest = self.updater.check_for_updates_now()
                if manifest:
                    ok = self.updater._download_and_verify(manifest)
                    if ok:
                        self.updater.apply_update_and_restart()
                    else:
                        QMessageBox.critical(self, "Update Failed", "Cryptographic verification or download failed.")
        else:
            QMessageBox.information(self, "Update", "Auto-updater not active in dev mode.")

    def _on_autostart_toggled(self, checked: bool):
        success = set_autostart_enabled(checked)
        if not success:
            self.chk_autostart.setChecked(not checked)
            QMessageBox.warning(self, "Auto-Start Error", "Unable to update Windows startup registry.")

    def test_connection(self):
        t0 = time.time()
        ok, res = self.backend.send_heartbeat(status="ACTIVE")
        elapsed = (time.time() - t0) * 1000
        if ok:
            self.lbl_conn_status.setText(f"● Status: CONNECTED & HEARTBEAT ACTIVE ({elapsed:.0f}ms)")
            self.lbl_conn_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_conn_status.setText(f"● Status: OFFLINE / DISCONNECTED ({res.get('error', 'Timeout')})")
            self.lbl_conn_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")

    def _on_sync_clicked(self):
        self.force_sync_requested.emit()
        stats = self.queue.get_queue_stats()
        self.lbl_q_stats.setText(f"Pending: {stats['pending']} | Synced Today: {stats['synced_today']} | Total: {stats['total']}")

    def _get_config_path(self) -> str:
        """Returns the path to config.json."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

    def _load_config_into_ui(self):
        """Loads saved config values from config.json into UI spinboxes."""
        config_path = self._get_config_path()
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if "active_interval_sec" in config:
                self.spin_rate.setValue(int(config["active_interval_sec"]))
            if "idle_timeout_sec" in config:
                self.spin_idle.setValue(int(config["idle_timeout_sec"]))
            if "audit_retention_sec" in config:
                self.spin_ttl.setValue(int(config["audit_retention_sec"]))
            if "update_channel" in config:
                idx = self.combo_channel.findText(config["update_channel"].capitalize())
                if idx >= 0:
                    self.combo_channel.setCurrentIndex(idx)
        except Exception:
            pass

    def _save_settings(self):
        """Persists all settings from UI controls to config.json."""
        config_path = self._get_config_path()

        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        config["active_interval_sec"] = self.spin_rate.value()
        config["idle_timeout_sec"] = self.spin_idle.value()
        config["audit_retention_sec"] = self.spin_ttl.value()
        config["update_channel"] = self.combo_channel.currentText().lower()

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self.settings_saved.emit()
            QMessageBox.information(self, "Settings Saved", "Configuration saved successfully to config.json.")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save settings: {e}")
