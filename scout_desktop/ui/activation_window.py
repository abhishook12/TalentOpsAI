"""
ui/activation_window.py — First-Run Device Onboarding & Activation Window

Provides a polished, zero-friction first-run setup modal:
- Enter short-lived activation code (TOS-XXXX-XXXX)
- Or catch deep-link: talentopsscout://activate?code=...
- Validates against TalentOps backend (/scout/activate)
- Stores secure JWT and device identity locally
- No database credentials, no Python configuration, no complex keys
"""

import sys
import logging
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon, QFont, QColor

logger = logging.getLogger("scout.activation")


class ActivationWindow(QDialog):
    activation_successful = Signal(dict)

    def __init__(self, backend_client, parent=None):
        super().__init__(parent)
        self.backend_client = backend_client

        self.setWindowTitle("TalentOps Scout — Connect Account")
        self.setFixedSize(480, 420)
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
                font-size: 18px;
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
                font-size: 14px;
                font-weight: 700;
                padding: 12px;
            }
            QPushButton#btnConnect:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
            QPushButton#btnConnect:disabled {
                background: #334155;
                color: #64748B;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

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

        lbl_sub = QLabel("Autonomous Continuous Intelligence")
        lbl_sub.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
        title_col.addWidget(lbl_sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Card container
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        lbl_instruction = QLabel("Connect this computer to your TalentOps account:")
        lbl_instruction.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 500;")
        card_layout.addWidget(lbl_instruction)

        # Activation Code Input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("TOS-XXXX-XXXX")
        self.code_input.setMaxLength(13)
        self.code_input.textChanged.connect(self._on_text_changed)
        self.code_input.returnPressed.connect(self._handle_connect)
        card_layout.addWidget(self.code_input)

        # Connect Button
        self.btn_connect = QPushButton("Connect Account")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self._handle_connect)
        card_layout.addWidget(self.btn_connect)

        # Status Label
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600;")
        card_layout.addWidget(self.lbl_status)

        layout.addWidget(card)

        # Instructions / Help
        help_layout = QVBoxLayout()
        help_layout.setSpacing(4)
        lbl_help_title = QLabel("How to get an activation code:")
        lbl_help_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        help_layout.addWidget(lbl_help_title)

        lbl_help_step = QLabel("1. Sign in to TalentOps Web (talent-ops-ai.vercel.app)\n2. Navigate to Talent Scout → Scout Nodes\n3. Click [Add Scout] to generate your 10-minute code")
        lbl_help_step.setStyleSheet("font-size: 11px; color: #94A3B8; line-height: 1.4;")
        help_layout.addWidget(lbl_help_step)

        layout.addLayout(help_layout)
        layout.addStretch()

    def set_code(self, code: str):
        """Auto-fills code when launched from deep link."""
        if code:
            self.code_input.setText(code.strip().upper())
            self._handle_connect()

    def _on_text_changed(self, text: str):
        # Auto-uppercase
        cursor_pos = self.code_input.cursorPosition()
        self.code_input.blockSignals(True)
        upper_text = text.upper()
        self.code_input.setText(upper_text)
        self.code_input.setCursorPosition(cursor_pos)
        self.code_input.blockSignals(False)

    def _handle_connect(self):
        code = self.code_input.text().strip().upper()
        if not code:
            self.lbl_status.setText("Please enter your activation code.")
            self.lbl_status.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
            return

        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Connecting...")
        self.lbl_status.setText("Validating code with TalentOps backend...")
        self.lbl_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        QApplication.processEvents()

        success, data = self.backend_client.activate_with_code(code)

        if success:
            self.lbl_status.setText(f"✅ Connected successfully as {data.get('user_email', 'User')}!")
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
