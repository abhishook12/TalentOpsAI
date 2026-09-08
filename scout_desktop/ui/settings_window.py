"""
ui/settings_window.py — Settings, Node Identity & Connection Status Window

Surface 4 of the TalentOps Scout Desktop architecture.
Provides configuration for:
- [✓] Start Scout with Windows (HKCU Run key)
- Node Identity (user_id, scout_id, device_id, session_id)
- Live Backend Connection Status & Heartbeat
- Telemetry & Staging Queue Management
"""

import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QFrame, QTabWidget, QLineEdit, QMessageBox,
    QSpinBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor

from ..core.autostart import is_autostart_enabled, set_autostart_enabled
from ..sync.backend_client import BackendClient
from ..sync.local_queue import LocalQueue


class SettingsWindow(QWidget):
    settings_saved = Signal()
    force_sync_requested = Signal()

    def __init__(self, backend_client: BackendClient, local_queue: LocalQueue, parent=None):
        super().__init__(parent)
        self.backend = backend_client
        self.queue = local_queue

        self.setWindowTitle("TalentOps Scout — Settings & Connection Status")
        self.resize(560, 480)

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
            QLineEdit, QSpinBox {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
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
        lbl_sub = QLabel("Autonomous Intelligence Companion Configuration & Health")
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

        # Initial check
        self.test_connection()

    def _on_autostart_toggled(self, checked: bool):
        success = set_autostart_enabled(checked)
        if not success:
            self.chk_autostart.setChecked(not checked)
            QMessageBox.warning(self, "Auto-Start Error", "Unable to update Windows startup registry.")

    def test_connection(self):
        import time
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
        except Exception:
            pass  # Config file may be malformed; use defaults

    def _save_settings(self):
        """Persists all settings from UI controls to config.json."""
        config_path = self._get_config_path()

        # Load existing config to preserve other keys
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        # Update config with current UI values
        config["active_interval_sec"] = self.spin_rate.value()
        config["idle_timeout_sec"] = self.spin_idle.value()
        config["audit_retention_sec"] = self.spin_ttl.value()

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self.settings_saved.emit()
            QMessageBox.information(self, "Settings Saved", "Configuration saved successfully to config.json.")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save settings: {e}")
