"""
ui/diagnostics_window.py — Developer Diagnostics & Evidence Grounding Inspector

Displays deep forensic evidence for the active capture:
- Recent Screenshot thumbnail
- Extraction Result JSON
- Source URL & Active Window HWND
- Capture ID & Visual Delta score
- Field Confidence & Grounding Evidence
- Staging and Master Database Sync Status
- Auto-Purge Timer
"""

import json
import os
import io
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QSplitter, QTabWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QIcon
from PIL import Image


class DiagnosticsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TalentOps Scout — Forensic Diagnostics")
        self.resize(780, 540)

        # Set Window Icon
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"),
            r"c:\TalentOpsAI\talentops-logo.png",
            r"c:\TalentOpsAI\frontend\public\talentops-logo.png",
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
                break

        self.setStyleSheet("""
            QWidget {
                background-color: #0b1120;
                color: #e2e8f0;
                font-family: 'Segoe UI', monospace;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background: #0b1120;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #0f172a;
                color: #94a3b8;
                padding: 6px 14px;
                border: 1px solid #1e293b;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #1e293b;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QTextEdit {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 6px;
                color: #38bdf8;
                font-size: 11px;
            }
            QLabel {
                font-size: 11px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Info Bar
        info_bar = QHBoxLayout()
        info_bar.setSpacing(8)

        # Brand Logo in header
        lbl_logo = QLabel()
        lbl_logo.setFixedSize(20, 20)
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"),
            r"c:\TalentOpsAI\talentops-logo.png",
            r"c:\TalentOpsAI\frontend\public\talentops-logo.png",
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    lbl_logo.setPixmap(pix.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    lbl_logo.setScaledContents(True)
                    break
        info_bar.addWidget(lbl_logo)

        self.lbl_capture_id = QLabel("Capture ID: —")
        self.lbl_capture_id.setStyleSheet("color: #a855f7; font-weight: bold;")
        info_bar.addWidget(self.lbl_capture_id)

        self.lbl_delta = QLabel("Visual Delta: —")
        self.lbl_delta.setStyleSheet("color: #38bdf8;")
        info_bar.addWidget(self.lbl_delta)

        self.lbl_grounding = QLabel("Grounding: —")
        self.lbl_grounding.setStyleSheet("color: #10b981; font-weight: bold;")
        info_bar.addWidget(self.lbl_grounding)

        info_bar.addStretch()
        layout.addLayout(info_bar)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Live Capture & Grounding
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Horizontal)

        # Left Panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("CAPTURED FRAME THUMBNAIL:"))
        self.lbl_thumbnail = QLabel("No Capture Available")
        self.lbl_thumbnail.setFixedSize(320, 200)
        self.lbl_thumbnail.setAlignment(Qt.AlignCenter)
        self.lbl_thumbnail.setStyleSheet("background-color: #020617; border: 1px solid #1e293b; border-radius: 6px;")
        left_layout.addWidget(self.lbl_thumbnail)

        self.lbl_win_meta = QLabel("Active Window: —\nPID: —\nURL: —")
        self.lbl_win_meta.setWordWrap(True)
        self.lbl_win_meta.setStyleSheet("color: #94a3b8; font-size: 10px;")
        left_layout.addWidget(self.lbl_win_meta)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # Right Panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("EXTRACTED ENTITIES & EVIDENCE GROUNDING:"))
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        right_layout.addWidget(self.txt_output)

        splitter.addWidget(right_widget)
        tab1_layout.addWidget(splitter)
        self.tabs.addTab(tab1, "Live Capture & Grounding")

        # Tab 2: Subsystem Health & Architecture
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.setContentsMargins(8, 8, 8, 8)
        tab2_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(8)

        # Card 1: Visual Sampler & Buffer
        c1 = QFrame()
        c1.setStyleSheet("background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        c1_lay = QVBoxLayout(c1)
        c1_lay.addWidget(QLabel("<b>VISUAL SAMPLER & BUFFER</b>"))
        self.lbl_sub_sampler = QLabel("State: ACTIVE\nThreshold: 3.5%\nBuffer Cap: 100 MB / 20 items\nPurge TTL: 20s")
        self.lbl_sub_sampler.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c1_lay.addWidget(self.lbl_sub_sampler)
        grid.addWidget(c1, 0, 0)

        # Card 2: Grounding Gate & Proof Chains
        c2 = QFrame()
        c2.setStyleSheet("background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        c2_lay = QVBoxLayout(c2)
        c2_lay.addWidget(QLabel("<b>EVIDENCE GROUNDING GATE</b>"))
        self.lbl_sub_grounding = QLabel("Min Confidence: 0.30\nStrict Mode: True\nSource Weighting: ACTIVE\nFabrication Defense: ACTIVE")
        self.lbl_sub_grounding.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c2_lay.addWidget(self.lbl_sub_grounding)
        grid.addWidget(c2, 0, 1)

        # Card 3: Context Memory & Identity
        c3 = QFrame()
        c3.setStyleSheet("background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        c3_lay = QVBoxLayout(c3)
        c3_lay.addWidget(QLabel("<b>CONTEXT MEMORY & IDENTITY</b>"))
        self.lbl_sub_memory = QLabel("Entity Contexts: Active\nTTL: 300s\nConflict Resolution: HIERARCHICAL\nTimeline Engine: ACTIVE")
        self.lbl_sub_memory.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c3_lay.addWidget(self.lbl_sub_memory)
        grid.addWidget(c3, 1, 0)

        # Card 4: Staging Queue & Backend
        c4 = QFrame()
        c4.setStyleSheet("background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 8px;")
        c4_lay = QVBoxLayout(c4)
        c4_lay.addWidget(QLabel("<b>LOCAL QUEUE & BACKEND SYNC</b>"))
        self.lbl_sub_sync = QLabel("SQLite Queue: Operational\nDead-Letter Queue: Active (max 5)\nBackoff: Exponential (10s-300s)\nPayload Compression: GZIP (>8KB)")
        self.lbl_sub_sync.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c4_lay.addWidget(self.lbl_sub_sync)
        grid.addWidget(c4, 1, 1)

        tab2_layout.addLayout(grid)
        tab2_layout.addStretch()
        self.tabs.addTab(tab2, "Subsystem Health & Architecture")

        layout.addWidget(self.tabs)

    def update_diagnostics(
        self,
        capture_id: str,
        delta: float,
        img: Image.Image,
        window_info: Any,
        url: str,
        entities_data: Any,
    ):
        """Updates developer diagnostics with live capture details."""
        self.lbl_capture_id.setText(f"Capture ID: {capture_id}")
        self.lbl_delta.setText(f"Visual Delta: {delta:.4f}")
        
        # Thumbnail conversion
        if img:
            try:
                thumb = img.copy()
                thumb.thumbnail((320, 200))
                buf = io.BytesIO()
                thumb.save(buf, format="PNG")
                qimg = QImage.fromData(buf.getvalue())
                self.lbl_thumbnail.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                pass

        # Window Meta
        w_title = getattr(window_info, "title", "Unknown") if window_info else "Unknown"
        w_pid = getattr(window_info, "pid", "—") if window_info else "—"
        w_proc = getattr(window_info, "process_name", "—") if window_info else "—"
        self.lbl_win_meta.setText(
            f"Process: {w_proc} (PID: {w_pid})\n"
            f"Window: {w_title}\n"
            f"URL: {url or 'None (Native App)'}"
        )

        # Entities formatting
        grounded_count = 0
        total_obs = 0
        if isinstance(entities_data, list):
            for cluster in entities_data:
                obs_list = getattr(cluster, "observations", [])
                total_obs += len(obs_list)
                grounded_count += sum(1 for o in obs_list if getattr(o, "grounding_status", "") == "GROUNDED")

        grounding_ratio = f"{grounded_count}/{total_obs} Grounded" if total_obs > 0 else "N/A"
        self.lbl_grounding.setText(f"Grounding: {grounding_ratio}")

        # JSON text dump
        try:
            if hasattr(entities_data, "to_staged_contact_dict"):
                dump = json.dumps(entities_data.to_staged_contact_dict(), indent=2)
            elif isinstance(entities_data, list) and entities_data and hasattr(entities_data[0], "to_staged_contact_dict"):
                dump = json.dumps([c.to_staged_contact_dict() for c in entities_data], indent=2)
            else:
                dump = str(entities_data)
        except Exception as e:
            dump = f"Serialization error: {e}"

        self.txt_output.setPlainText(dump)
