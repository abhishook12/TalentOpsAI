"""
ui/activation_window.py — Device Onboarding & Account Pairing Window

Dual-Mode Pairing:
Mode 1 (Primary / Recommended): Reverse Device Flow
- App calls /scout/device-flow/init to get human-friendly code (e.g. TOS-8492)
- Shows code prominently with [Copy] button
- Instructs user: Go to talent-ops-ai.vercel.app/download-scout and enter this code
- Polls /scout/device-flow/status every 2 seconds
- When verified on web, automatically activates, saves credentials, and starts!

Mode 2 (Manual Fallback):
- Enter an admin activation code (TOS-XXXX-XXXX) directly into the app
"""

import sys
import logging
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QFont, QColor

logger = logging.getLogger("scout.activation")


class ActivationWindow(QDialog):
    activation_successful = Signal(dict)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend_client = backend_client
        self._current_pairing_code: Optional[str] = None
        self._is_manual_mode = False

        self.setWindowTitle("TalentOps Scout — Connect Account")
        self.setFixedSize(500, 480)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0E14;
                color: #F8FAFC;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QFrame#cardFrame {
                background-color: #131722;
                border: 1px solid #1E2433;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #0E131F;
                border: 1.5px solid #334155;
                border-radius: 8px;
                color: #F8FAFC;
                font-family: "Cascadia Code", "Consolas", monospace;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 10px 14px;
                text-align: center;
            }
            QLineEdit:focus {
                border-color: #10B981;
                background-color: #131B2E;
            }
            QPushButton#btnConnect {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 10px;
            }
            QPushButton#btnConnect:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
            QPushButton#btnCopy {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
            }
            QPushButton#btnCopy:hover {
                background: #334155;
            }
            QPushButton#btnToggleMode {
                background: transparent;
                border: none;
                color: #38bdf8;
                font-size: 11px;
                text-decoration: underline;
            }
        """)

        self._build_ui()

        # Poller timer for web verification
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_status)

        # Initialize Device Flow pairing code on startup
        QTimer.singleShot(100, self._init_pairing_code)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header with Logo / Icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel("🛰️")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel("TalentOps Scout")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #F8FAFC;")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Autonomous Sourcing Companion")
        lbl_sub.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
        title_col.addWidget(lbl_sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Main Card container
        self.card = QFrame()
        self.card.setObjectName("cardFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 20, 20, 20)
        self.card_layout.setSpacing(12)

        # --- PRIMARY VIEW: REVERSE DEVICE FLOW ---
        self.flow_container = QWidget()
        flow_layout = QVBoxLayout(self.flow_container)
        flow_layout.setContentsMargins(0, 0, 0, 0)
        flow_layout.setSpacing(10)

        lbl_flow_title = QLabel("Pair this computer to your account:")
        lbl_flow_title.setStyleSheet("font-size: 13px; color: #cbd5e1; font-weight: 600;")
        flow_layout.addWidget(lbl_flow_title)

        lbl_step1 = QLabel("1. In your browser, go to Desktop Scout on the website.")
        lbl_step1.setStyleSheet("font-size: 11px; color: #94a3b8;")
        flow_layout.addWidget(lbl_step1)

        lbl_step2 = QLabel("2. Enter this pairing code to connect this computer:")
        lbl_step2.setStyleSheet("font-size: 11px; color: #94a3b8;")
        flow_layout.addWidget(lbl_step2)

        # Code Box
        code_box = QFrame()
        code_box.setStyleSheet("background-color: #090d16; border: 1.5px dashed #38bdf8; border-radius: 8px; padding: 12px;")
        code_box_layout = QHBoxLayout(code_box)
        code_box_layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_code_display = QLabel("TOS-....")
        self.lbl_code_display.setStyleSheet("font-family: monospace; font-size: 24px; font-weight: 800; color: #38bdf8; letter-spacing: 3px;")
        code_box_layout.addWidget(self.lbl_code_display)
        code_box_layout.addStretch()

        self.btn_copy_code = QPushButton("📋 Copy")
        self.btn_copy_code.setObjectName("btnCopy")
        self.btn_copy_code.clicked.connect(self._copy_code)
        code_box_layout.addWidget(self.btn_copy_code)

        flow_layout.addWidget(code_box)

        # Waiting / polling indicator
        self.lbl_poll_status = QLabel("⏳ Waiting for you to enter code on website...")
        self.lbl_poll_status.setStyleSheet("font-size: 11px; color: #f59e0b; font-style: italic;")
        self.lbl_poll_status.setAlignment(Qt.AlignCenter)
        flow_layout.addWidget(self.lbl_poll_status)

        self.card_layout.addWidget(self.flow_container)

        # --- SECONDARY VIEW: MANUAL CODE ENTRY ---
        self.manual_container = QWidget()
        manual_layout = QVBoxLayout(self.manual_container)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(10)

        lbl_manual_title = QLabel("Enter Activation Code from Admin:")
        lbl_manual_title.setStyleSheet("font-size: 13px; color: #cbd5e1; font-weight: 600;")
        manual_layout.addWidget(lbl_manual_title)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("TOS-XXXX-XXXX")
        self.code_input.setMaxLength(14)
        self.code_input.returnPressed.connect(self._handle_manual_connect)
        manual_layout.addWidget(self.code_input)

        self.btn_connect = QPushButton("Connect Account")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self._handle_manual_connect)
        manual_layout.addWidget(self.btn_connect)

        self.card_layout.addWidget(self.manual_container)
        self.manual_container.hide()  # Hidden by default

        # Status / Feedback label
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.card_layout.addWidget(self.lbl_status)

        layout.addWidget(self.card)

        # Toggle between Web Verification and Manual Code Entry
        self.btn_toggle = QPushButton("Have an admin activation code? Enter it manually")
        self.btn_toggle.setObjectName("btnToggleMode")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle_mode)
        layout.addWidget(self.btn_toggle, alignment=Qt.AlignCenter)

        layout.addStretch()

    def _init_pairing_code(self):
        """Initializes Reverse Device Flow code with backend."""
        self.lbl_poll_status.setText("Connecting to TalentOps network...")
        ok, data = self.backend_client.init_device_flow()
        if ok and data.get("code"):
            self._current_pairing_code = data["code"]
            self.lbl_code_display.setText(self._current_pairing_code)
            self.lbl_poll_status.setText("⏳ Waiting for you to verify on website...")
            self.lbl_poll_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.poll_timer.start(2500)
        else:
            err = data.get("error", "Could not reach server")
            self.lbl_poll_status.setText(f"Offline / Connection issue: {err}")
            self.lbl_poll_status.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _copy_code(self):
        if self._current_pairing_code:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._current_pairing_code)
            self.btn_copy_code.setText("✓ Copied!")
            QTimer.singleShot(2000, lambda: self.btn_copy_code.setText("📋 Copy"))

    def _poll_status(self):
        if not self._current_pairing_code:
            return

        ok, data = self.backend_client.poll_device_flow(self._current_pairing_code)
        if ok:
            # Successfully approved on web!
            self.poll_timer.stop()
            user_name = data.get("user_name") or data.get("user_email") or "User"
            self.lbl_poll_status.setText(f"🎉 Linked to {user_name}! Launching Scout...")
            self.lbl_poll_status.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 700;")
            self.activation_successful.emit(data)
            QTimer.singleShot(1500, self.accept)
        elif data.get("status") == "EXPIRED":
            self.poll_timer.stop()
            self.lbl_poll_status.setText("Code expired. Click to generate a new one.")
            self.lbl_poll_status.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _toggle_mode(self):
        self._is_manual_mode = not self._is_manual_mode
        if self._is_manual_mode:
            self.flow_container.hide()
            self.manual_container.show()
            self.poll_timer.stop()
            self.btn_toggle.setText("← Back to automatic web pairing code")
            self.code_input.setFocus()
        else:
            self.manual_container.hide()
            self.flow_container.show()
            self.btn_toggle.setText("Have an admin activation code? Enter it manually")
            if self._current_pairing_code:
                self.poll_timer.start(2500)

    def _handle_manual_connect(self):
        code = self.code_input.text().strip().upper()
        if not code:
            self.lbl_status.setText("Please enter your activation code.")
            self.lbl_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
            return

        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Connecting...")
        self.lbl_status.setText("Validating code with backend...")
        self.lbl_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        QApplication.processEvents()

        success, data = self.backend_client.activate_with_code(code)

        if success:
            user_email = data.get("user_email", "User")
            self.lbl_status.setText(f"✅ Connected successfully as {user_email}!")
            self.lbl_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 700;")
            self.btn_connect.setText("Connected")
            self.activation_successful.emit(data)
            self.accept()
        else:
            err = data.get("error", "Activation failed")
            self.lbl_status.setText(f"❌ {err}")
            self.lbl_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("Connect Account")

    def closeEvent(self, event):
        self.poll_timer.stop()
        super().closeEvent(event)
