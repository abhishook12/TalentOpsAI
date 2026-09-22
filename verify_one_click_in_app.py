import sys
import os
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from scout_desktop.version import __version__
from scout_desktop.ui.components import LeftRail, TopBar
from scout_desktop.ui.main_window import MainWindow
from scout_desktop.ui.notifications_window import UpdateCenterDialog

print("=== VERIFYING ONE-CLICK IN-APP UPDATE SYSTEM (RULE 11) ===")

# CHECK 1: LeftRail Sidebar 1-Click Update Card & Signal
print("\n[CHECK 1] Left Rail Sidebar 1-Click Update Component:")
rail = LeftRail()
assert hasattr(rail, "update_card"), "LeftRail missing update_card"
assert hasattr(rail, "btn_rail_update"), "LeftRail missing btn_rail_update"
assert hasattr(rail, "update_center_requested"), "LeftRail missing update_center_requested signal"

print(f"✓ LeftRail Update Button Text: '{rail.btn_rail_update.text()}'")
assert "Download & Update" in rail.btn_rail_update.text()

emitted = []
rail.update_center_requested.connect(lambda: emitted.append(True))
rail.btn_rail_update.click()
assert len(emitted) == 1, "Clicking 1-Click Update button did not emit update_center_requested"
print("✓ Clicking LeftRail '⚡ Download & Update' successfully emitted signal.")
print(">>> CHECK 1 PASSED: Sidebar 1-Click Update Component 100% verified.")

# CHECK 2: MainWindow Wiring & Signal Routing
print("\n[CHECK 2] MainWindow Signal Routing:")
main_win = MainWindow()
assert hasattr(main_win, "show_update_center")
opened = []
main_win.show_update_center = lambda: opened.append(True)

# Trigger from left rail
main_win.left_rail.btn_rail_update.click()
assert len(opened) == 1, "MainWindow failed to open Update Center from LeftRail click"
print("✓ LeftRail button directly triggers MainWindow.show_update_center.")

# Trigger from TopBar version pill
main_win.top_bar.btn_version_chip.click()
assert len(opened) == 2, "MainWindow failed to open Update Center from TopBar chip click"
print("✓ TopBar version pill directly triggers MainWindow.show_update_center.")
print(">>> CHECK 2 PASSED: In-App 1-Click triggers correctly wired.")

# CHECK 3: UpdateCenterDialog 1-Click Action & Renewal State
print("\n[CHECK 3] UpdateCenterDialog 1-Click Execution:")
dlg = UpdateCenterDialog()

# Test Up-to-Date state (should still allow 1-click renewal / re-install)
manifest_current = {
    "version": __version__,
    "latest_version": __version__,
    "download_url": "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe",
    "release_notes": "Up to date."
}
dlg._apply_manifest_result(manifest_current)
assert dlg.btn_update.isEnabled() == True, "Update button should be enabled for 1-click renewal"
assert "1-Click" in dlg.btn_update.text()
assert "Re-install" in dlg.btn_update.text()
print(f"✓ Up-to-Date 1-Click renewal button text: '{dlg.btn_update.text()}'")

# Test Update Available state
manifest_new = {
    "version": "2.9.4",
    "latest_version": "2.9.4",
    "download_url": "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe",
    "release_notes": "Version 2.9.4 ready."
}
dlg._apply_manifest_result(manifest_new)
assert dlg.btn_update.isEnabled() == True
assert "Update to v2.9.4 (1-Click)" in dlg.btn_update.text()
print(f"✓ Update Available 1-Click button text: '{dlg.btn_update.text()}'")
print(">>> CHECK 3 PASSED: 1-Click update and renewal logic fully verified.")

print("\n========================================================")
print("ALL 3 IN-APP ONE-CLICK UPDATE CHECKS PASSED!")
print("========================================================")
