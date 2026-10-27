"""
qt_chat_desktop_app.py — Authentic Qt6 Desktop Messenger for High-Speed Automation
===================================================================================
A real native Qt6 Windows application (same framework as Vitel Global: Qt6 / QWindowIcon)
designed for ultra-fast, zero-disturbance background messaging automation practice.
"""

import sys
import os
import json
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QTextEdit,
    QScrollArea, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap

STATE_PATH = Path(r"c:\TalentOpsAI\sandbox\qt_chat_state.json")
SCREENSHOT_DIR = Path(r"C:\Users\User\.gemini\antigravity\brain\214ed49c-e342-4591-af17-961c9f050572")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CONTACTS = [
    "+1 (972) 419-1616",
    "+1 (972) 419-1607",
    "+1 (972) 419-1615",
    "+1 (516) 510-6582",
    "+1 (414) 217-6217",
    "+1 (262) 409-1002",
    "+1 (145) 674-5646",
    "+1 (801) 870-6007",
    "+1 (262) 567-8166",
    "+1 (414) 773-0679",
    "+1 (646) 421-2155",
    "+1 (717) 628-9614",
    "+1 (860) 331-9007",
    "+1 (860) 404-8883",
    "+1 (860) 678-1300",
    "+1 (860) 439-5069",
    "+1 (724) 584-3567",
    "+1 (817) 845-1837",
    "+1 (972) 419-1629",
    "+1 (774) 328-1700"
]

class QtChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TalentOps Qt6 Desktop Messenger (Simulation Sandbox)")
        self.resize(920, 640)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QWidget { color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #334155;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
            }
            QTextEdit#myInput {
                background-color: #1e293b;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                padding: 8px;
            }
            QPushButton#sendBtn {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton#sendBtn:hover {
                background-color: #1d4ed8;
            }
        """)

        self.histories = {c: [] for c in CONTACTS}
        self.active_index = 0
        self.total_sent = 0

        self._init_ui()
        self.select_contact(0)
        self.save_state()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left Column: Contacts List
        left_box = QVBoxLayout()
        header_left = QLabel("Conversations (Top 20)")
        header_left.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_left.setStyleSheet("color: #94a3b8; margin-bottom: 4px;")
        left_box.addWidget(header_left)

        self.contact_list = QListWidget()
        for idx, c in enumerate(CONTACTS):
            item = QListWidgetItem(f"{idx+1:02d}. {c}")
            item.setSizeHint(QSize(240, 44))
            self.contact_list.addItem(item)
        self.contact_list.currentRowChanged.connect(self.select_contact)
        left_box.addWidget(self.contact_list)

        main_layout.addLayout(left_box, stretch=1)

        # Right Column: Active Chat Area
        right_box = QVBoxLayout()
        right_box.setSpacing(8)

        # Chat Header
        self.chat_header = QLabel("+1 (972) 419-1616")
        self.chat_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.chat_header.setStyleSheet("color: #60a5fa; padding: 6px 0;")
        right_box.addWidget(self.chat_header)

        # Message Stream (List Widget styled as chat bubbles)
        self.msg_stream = QListWidget()
        self.msg_stream.setStyleSheet("""
            QListWidget {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
            }
            QListWidget::item {
                background-color: #1e3a8a;
                color: #ffffff;
                border-radius: 8px;
                margin-bottom: 8px;
                padding: 10px 14px;
            }
        """)
        right_box.addWidget(self.msg_stream, stretch=1)

        # Input Area
        input_row = QHBoxLayout()
        self.input_edit = QTextEdit()
        self.input_edit.setObjectName("myInput")
        self.input_edit.setPlaceholderText("Type a message or paste payload here...")
        self.input_edit.setFixedHeight(70)
        input_row.addWidget(self.input_edit, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedHeight(70)
        self.send_btn.clicked.connect(self.handle_send)
        input_row.addWidget(self.send_btn)

        right_box.addLayout(input_row)
        main_layout.addLayout(right_box, stretch=2)

    def select_contact(self, index: int):
        if 0 <= index < len(CONTACTS):
            self.active_index = index
            target = CONTACTS[index]
            self.chat_header.setText(f"{index+1}. {target}  •  Online")
            self.msg_stream.clear()
            for msg in self.histories[target]:
                self._add_msg_bubble(msg["text"], msg["time"])

    def _add_msg_bubble(self, text: str, time_str: str):
        item = QListWidgetItem(f"[{time_str}] Sent:\n{text}")
        item.setFont(QFont("Segoe UI", 10))
        self.msg_stream.addItem(item)
        self.msg_stream.scrollToBottom()

    def handle_send(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        target = CONTACTS[self.active_index]
        t_str = time.strftime("%H:%M:%S")
        entry = {
            "chat_index": self.active_index + 1,
            "target": target,
            "text": text,
            "time": t_str,
            "timestamp": time.time(),
            "has_smiley": "😃" in text or "\U0001f603" in text,
            "has_handshake": "🤝" in text or "\U0001f91d" in text
        }
        self.histories[target].append(entry)
        self.total_sent += 1
        self._add_msg_bubble(text, t_str)
        self.input_edit.clear()
        self.save_state()

    def save_state(self):
        state = {
            "window_title": self.windowTitle(),
            "active_index": self.active_index,
            "active_target": CONTACTS[self.active_index],
            "total_sent": self.total_sent,
            "histories": self.histories,
            "last_updated": time.time()
        }
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def capture_screenshot(self, filename: str) -> str:
        out_path = SCREENSHOT_DIR / filename
        pixmap = self.grab()
        pixmap.save(str(out_path), "PNG")
        return str(out_path)

def main():
    app = QApplication(sys.argv)
    win = QtChatWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
