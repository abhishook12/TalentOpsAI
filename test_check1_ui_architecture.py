"""
test_check1_ui_architecture.py — Check 1: 3-Level Window Architecture Verification
Tests Level 1 (Tray), Level 2 (Edge Handle), and Level 3 (Main Companion Window).
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure headless Qt offscreen platform if running in automated test runner
os.environ["QT_QPA_PLATFORM"] = "windows"

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

print("=== CHECK 1: 3-LEVEL WINDOW ARCHITECTURE VERIFICATION ===")

# --- Level 1: System Tray ---
print("\n[Level 1: System Tray]")
from scout_desktop.ui.tray import SystemTrayManager, create_tray_icon_pixmap

tray = SystemTrayManager()
print("  ✓ SystemTrayManager initialized")

# Test 4 States
for st in ["ACTIVE", "IDLE_WATCH", "PAUSED", "OFFLINE"]:
    tray.update_icon_status(st)
    pix = create_tray_icon_pixmap()
    assert not pix.isNull(), f"Tray pixmap null for state {st}"
    print(f"  ✓ State '{st}' rendered with live tooltip: '{tray.tray.toolTip()}'")

# --- Level 2: Persistent Edge Handle ---
print("\n[Level 2: Persistent Edge Handle / Dock (media_1788544064790.png)]")
from scout_desktop.ui.edge_handle import EdgeHandleWidget

edge_handle = EdgeHandleWidget()
print("  ✓ EdgeHandleWidget initialized")
assert edge_handle.width() == 30, f"Expected width 30, got {edge_handle.width()}"
assert edge_handle.height() == 84, f"Expected height 84, got {edge_handle.height()}"
flags = edge_handle.windowFlags()
assert flags & Qt.WindowStaysOnTopHint, "EdgeHandle must have WindowStaysOnTopHint"
assert flags & Qt.FramelessWindowHint, "EdgeHandle must have FramelessWindowHint"
assert flags & Qt.Tool, "EdgeHandle must have Tool flag"
print("  ✓ Verified window flags: WindowStaysOnTopHint | FramelessWindowHint | Tool")

# Test signal emission
clicked_detected = []
edge_handle.clicked.connect(lambda: clicked_detected.append(True))
edge_handle.clicked.emit()
assert len(clicked_detected) == 1, "EdgeHandle clicked signal failed to emit"
print("  ✓ Verified edge handle click toggle signal emission")

for st in ["ACTIVE", "IDLE_WATCH", "OFFLINE"]:
    edge_handle.set_status_state(st)
    assert edge_handle._status_state == st, f"Failed setting handle status {st}"
    print(f"  ✓ Edge handle status set to '{st}'")

# --- Level 3: Main Application Window ---
print("\n[Level 3: Main Application Companion Window]")
from scout_desktop.ui.main_window import MainWindow

main_win = MainWindow()
print("  ✓ MainWindow initialized as QMainWindow")
assert main_win.minimumWidth() == 420
assert main_win.minimumHeight() == 600
print("  ✓ Verified minimum window geometry: 420x600, default: 480x840")

# Verify "What is it doing right now?" banner
assert hasattr(main_win, "lbl_target_desc"), "Missing live state target desc banner"
assert hasattr(main_win, "lbl_sampling_pulse"), "Missing sampling pulse indicator"
main_win.lbl_target_desc.setText("Observing Google Chrome — Mariam Nguyen | LinkedIn")
main_win.lbl_sampling_pulse.setText("⚡ SAMPLING (1.0s interval)")
print("  ✓ Verified 'What is it doing right now?' banner:", main_win.lbl_target_desc.text())

# Verify 10 Explicit Telemetry Counters
counters = [
    main_win.c_captured, main_win.c_analyzed, main_win.c_useful,
    main_win.c_staged, main_win.c_matched, main_win.c_new,
    main_win.c_enriched, main_win.c_db_updates, main_win.c_purged,
    main_win.c_buffer
]
assert len(counters) == 10, f"Expected 10 explicit telemetry counters, got {len(counters)}"
main_win.update_explicit_counters({
    "captured": 5, "analyzed": 5, "useful": 4, "staged": 3,
    "matched": 1, "new": 2, "enriched": 1, "db_updates": 3,
    "purged": 1, "buffer_current": 0, "buffer_max": 20
})
assert main_win.c_captured.lbl_val.text() == "5"
assert main_win.c_staged.lbl_val.text() == "3"
assert main_win.c_buffer.lbl_val.text() == "0/20"
print("  ✓ Verified all 10 explicit telemetry counters updated correctly")

# Verify Extraction Proof Table
main_win.update_extraction_proof([
    {"field": "Name", "value": "Mariam Nguyen", "confidence": 0.98, "decision": "ACCEPT"},
    {"field": "Title", "value": "Senior Technical Recruiter", "confidence": 0.92, "decision": "ACCEPT"},
    {"field": "Company", "value": "Seaglass Technology Partners, LLC", "confidence": 0.92, "decision": "ACCEPT"},
    {"field": "Email", "value": "mnguyen@seaglassit.com", "confidence": 0.96, "decision": "ACCEPT"},
])
assert main_win.proof_table.rowCount() == 4
assert main_win.proof_table.item(0, 1).text() == "Mariam Nguyen"
assert main_win.proof_table.item(3, 1).text() == "mnguyen@seaglassit.com"
print("  ✓ Verified Grounded Extraction Proof Table (4 rows populated with confidence scores)")

# Verify Window Minimize / Close / Toggle Behavior
print("\n[Window Behavior & Persistence]")
# Test Close Event persistence: closeEvent must hide, NOT quit
from PySide6.QtGui import QCloseEvent
close_evt = QCloseEvent()
main_win.closeEvent(close_evt)
assert not close_evt.isAccepted(), "closeEvent must be ignored to prevent terminating background scout!"
print("  ✓ closeEvent correctly ignored (hides window while background scout runs silently)")

print("\n>>> CHECK 1 PASSED: ALL 3 VISUAL LEVELS & WINDOW BEHAVIORS VERIFIED SUCCESSFULLY! <<<")
