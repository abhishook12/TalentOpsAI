import sys
import os
import json
import threading
import datetime
import keyboard
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                               QLabel, QLineEdit, QHBoxLayout, QComboBox,
                               QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, QRect, Signal, QObject, QSharedMemory, QSettings
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QIcon

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "window_state.json")


class UIUpdater(QObject):
    update_status = Signal(str)
    update_stats = Signal(dict)
    update_action = Signal(str)
    stop_ui = Signal()


class RegionSelector(QWidget):
    region_selected = Signal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.showFullScreen()
        self.start_pos = None
        self.current_rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.current_rect = QRect(self.start_pos, self.start_pos)

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_rect = QRect(self.start_pos, event.globalPosition().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_rect:
            self.region_selected.emit(self.current_rect)
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if self.current_rect:
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.SolidLine))
            painter.drawRect(self.current_rect)
            painter.fillRect(self.current_rect, QColor(255, 0, 0, 30))


class OverlayUI(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_region = None
        self.is_running = False
        self.is_paused = False

        self.updater = UIUpdater()
        self.updater.update_status.connect(self.set_status_text)
        self.updater.update_stats.connect(self.update_stats_display)
        self.updater.update_action.connect(self.set_action_text)
        self.updater.stop_ui.connect(self.stop_extraction)

        keyboard.on_press_key("esc", lambda _: self.emergency_stop())

        self.initUI()
        self._load_window_state()

    def emergency_stop(self):
        if self.is_running:
            self.stop_extraction()
            self.updater.update_status.emit("EMERGENCY STOP (Esc Pressed)")

    def set_status_text(self, text):
        self.status_label.setText(f"Status: {text}")

    def set_action_text(self, text):
        self.lbl_action.setText(text)

    def update_stats_display(self, stats):
        mapping = {
            "scroll":           self.lbl_scroll,
            "visible_messages": self.lbl_vis_msgs,
            "processing":       self.lbl_processing,
            "saved":            self.lbl_saved,
            "skipped":          self.lbl_skipped,
            "failed":           self.lbl_failed,
            "clipboard":        self.lbl_clipboard,
        }
        for key, widget in mapping.items():
            if key in stats:
                widget.setText(str(stats[key]))

    def initUI(self):
        self.setWindowTitle("Teams Extractor")
        # Normal window with minimize, maximize, close, resizable
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint |
                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint |
                            Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #e0e0e0; font-family: Segoe UI; font-size: 11px; }
            QPushButton { border: 1px solid #555; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #3a3a3a; }
            QComboBox { border: 1px solid #555; border-radius: 3px; padding: 3px; background-color: #333; }
            QLineEdit { border: 1px solid #555; border-radius: 3px; padding: 3px; background-color: #333; }
            QLabel { border: none; }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Title
        title = QLabel("Teams Extractor")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4FC3F7; padding: 4px;")
        layout.addWidget(title)

        # Region Selection
        self.btn_select_area = QPushButton("Select Teams Chat Area")
        self.btn_select_area.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_select_area.clicked.connect(self.start_region_selection)
        layout.addWidget(self.btn_select_area)

        self.region_label = QLabel("Region: Not Selected")
        self.region_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.region_label)

        # ── Progress Grid ──
        stats_layout = QGridLayout()
        stats_layout.setSpacing(4)
        row = 0

        stats_data = [
            ("Current Scroll:",      "lbl_scroll",     "0"),
            ("Visible Messages:",    "lbl_vis_msgs",   "0"),
            ("Processing Message:",  "lbl_processing", "-"),
            ("Saved Messages:",      "lbl_saved",      "0"),
            ("Skipped (Duplicates):", "lbl_skipped",    "0"),
            ("Failed Selections:",   "lbl_failed",     "0"),
            ("Clipboard Status:",    "lbl_clipboard",  "-"),
            ("Current Action:",      "lbl_action",     "Idle"),
        ]

        for label_text, attr_name, default in stats_data:
            lbl_key = QLabel(label_text)
            lbl_key.setStyleSheet("color: #aaa;")
            lbl_val = QLabel(default)
            lbl_val.setStyleSheet("color: white; font-weight: bold;")
            stats_layout.addWidget(lbl_key, row, 0)
            stats_layout.addWidget(lbl_val, row, 1)
            setattr(self, attr_name, lbl_val)
            row += 1

        layout.addLayout(stats_layout)

        # Status
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 4px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # ── Settings ──
        settings0 = QHBoxLayout()
        settings0.addWidget(QLabel("Scroll Direction:"))
        self.scroll_dir_combo = QComboBox()
        self.scroll_dir_combo.addItems(["Up", "Down"])
        self.scroll_dir_combo.setCurrentText("Up")
        settings0.addWidget(self.scroll_dir_combo)
        layout.addLayout(settings0)

        settings1 = QHBoxLayout()
        settings1.addWidget(QLabel("Scroll Delay:"))
        self.scroll_delay_combo = QComboBox()
        self.scroll_delay_combo.setEditable(True)
        self.scroll_delay_combo.addItems(["0.5", "1", "2", "2.5", "3", "5", "10"])
        self.scroll_delay_combo.setCurrentText("2.5")
        settings1.addWidget(self.scroll_delay_combo)

        settings1.addWidget(QLabel("Scroll Overlap:"))
        self.scroll_overlap_combo = QComboBox()
        self.scroll_overlap_combo.setEditable(True)
        self.scroll_overlap_combo.addItems(["25%", "35%", "50%"])
        self.scroll_overlap_combo.setCurrentText("35%")
        settings1.addWidget(self.scroll_overlap_combo)
        layout.addLayout(settings1)

        settings2 = QHBoxLayout()
        settings2.addWidget(QLabel("Maximum Scrolls:"))
        self.max_scrolls_combo = QComboBox()
        self.max_scrolls_combo.setEditable(True)
        self.max_scrolls_combo.addItems(["100", "500", "1000", "Unlimited"])
        self.max_scrolls_combo.setCurrentText("500")
        settings2.addWidget(self.max_scrolls_combo)

        settings2.addWidget(QLabel("Stop Text:"))
        self.stop_input = QLineEdit()
        self.stop_input.setPlaceholderText("Optional...")
        settings2.addWidget(self.stop_input)
        layout.addLayout(settings2)

        # ── Buttons ──
        self.btn_debug = QPushButton("Test Detect Messages (Debug)")
        self.btn_debug.setStyleSheet("background-color: #2196F3; color: white;")
        self.btn_debug.clicked.connect(self.run_debug_test)
        layout.addWidget(self.btn_debug)

        btn_row1 = QHBoxLayout()
        self.btn_start = QPushButton("Start Extraction")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(lambda: self.start_extraction())
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_stop.clicked.connect(self.stop_extraction)
        btn_row1.addWidget(self.btn_start)
        btn_row1.addWidget(self.btn_pause)
        btn_row1.addWidget(self.btn_stop)
        layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_open_out = QPushButton("Output Folder")
        self.btn_open_out.clicked.connect(self.open_output_folder)
        btn_row2.addWidget(self.btn_open_out)
        layout.addLayout(btn_row2)

        self.setLayout(layout)
        self.setMinimumSize(380, 500)
        self.resize(440, 580)

    # ── Window State Persistence ──
    def _load_window_state(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    state = json.load(f)
                self.move(state.get("x", 100), state.get("y", 50))
                self.resize(state.get("w", 440), state.get("h", 580))
                return
        except Exception:
            pass
        # Default position: top-right
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 50)

    def _save_window_state(self):
        try:
            state = {
                "x": self.x(), "y": self.y(),
                "w": self.width(), "h": self.height(),
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_window_state()
        self.is_running = False
        event.accept()

    # ── Actions ──
    def start_region_selection(self):
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.show()

    def on_region_selected(self, rect):
        self.selected_region = (rect.x(), rect.y(), rect.width(), rect.height())
        self.region_label.setText(f"Region: {self.selected_region}")

    def run_debug_test(self):
        if not self.selected_region:
            self.set_status_text("Error - Select a region first!")
            return
        config = {
            "region": self.selected_region,
            "output_dir": OUTPUT_DIR,
            "session_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
        import automation
        self.thread = threading.Thread(target=automation.test_detect_messages, args=(self, config))
        self.thread.daemon = True
        self.thread.start()

    def start_extraction(self):
        if not self.selected_region:
            self.set_status_text("Error - Select a region first!")
            return

        self.is_running = True
        self.is_paused = False
        self.btn_start.setEnabled(False)
        self.btn_pause.setText("Pause")

        # Parse values safely in case user types invalid text
        overlap_text = self.scroll_overlap_combo.currentText()
        try:
            overlap_pct = int(overlap_text.replace("%", "").strip()) / 100.0
        except ValueError:
            overlap_pct = 0.35

        max_str = self.max_scrolls_combo.currentText().strip()
        try:
            max_scrolls = 999999 if max_str.lower() == "unlimited" else int(max_str)
        except ValueError:
            max_scrolls = 500
            
        try:
            delay_val = float(self.scroll_delay_combo.currentText().strip())
        except ValueError:
            delay_val = 2.5

        config = {
            "region": self.selected_region,
            "direction": self.scroll_dir_combo.currentText(),
            "overlap_pct": overlap_pct,
            "delay": delay_val,
            "stop_text": self.stop_input.text().strip(),
            "max_scrolls": max_scrolls,
            "output_dir": OUTPUT_DIR,
            "session_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        }

        import automation
        import importlib
        importlib.reload(automation)

        self.thread = threading.Thread(target=automation.run_extraction_loop, args=(self, config))
        self.thread.daemon = True
        self.thread.start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.setText("Resume" if self.is_paused else "Pause")
        self.set_status_text("Paused" if self.is_paused else "Resumed")

    def stop_extraction(self):
        self.is_running = False
        self.set_status_text("Stopping...")
        self.btn_start.setEnabled(True)

    def open_output_folder(self):
        os.startfile(OUTPUT_DIR)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Teams Extractor")

    # Single Instance Logic
    shared_mem = QSharedMemory("TeamsExtractorSharedMem")
    if shared_mem.attach():
        try:
            import win32gui
            import win32con
            hwnd = win32gui.FindWindow(None, "Teams Extractor")
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        sys.exit(0)

    shared_mem.create(1)

    ex = OverlayUI()
    ex.show()
    sys.exit(app.exec())
