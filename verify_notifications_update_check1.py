import sys
import os
import unittest
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from scout_desktop.version import __version__
from scout_desktop.ui.components import TopBar
from scout_desktop.ui.notifications_window import UpdateCenterDialog, NotificationsDialog
from scout_desktop.ui.main_window import MainWindow

print("=== CHECK 1: DESKTOP SCOUT TOPBAR & UPDATE/NOTIFICATIONS DIALOGS TEST ===")

# 1. Test TopBar interactive components
top_bar = TopBar()

# Check version chip exists and is a QPushButton
assert hasattr(top_bar, "btn_version_chip"), "TopBar missing btn_version_chip"
print(f"1. TopBar version chip detected: '{top_bar.btn_version_chip.text()}'")
assert top_bar.btn_version_chip.text() == f"v{__version__}"

# Check notification bell exists and is a QPushButton
assert hasattr(top_bar, "btn_notifications"), "TopBar missing btn_notifications"
print(f"2. TopBar notification button detected: '{top_bar.btn_notifications.text()}'")
assert "🔔" in top_bar.btn_notifications.text()

# Test signals
update_clicked = []
top_bar.update_center_requested.connect(lambda: update_clicked.append(True))
top_bar.btn_version_chip.click()
assert len(update_clicked) == 1, "Clicking version chip did not emit update_center_requested"
print("3. Version chip click successfully emitted update_center_requested signal.")

notif_clicked = []
top_bar.notifications_requested.connect(lambda: notif_clicked.append(True))
top_bar.btn_notifications.click()
assert len(notif_clicked) == 1, "Clicking notification bell did not emit notifications_requested"
print("4. Notification bell click successfully emitted notifications_requested signal.")

# Test state updates on TopBar
top_bar.set_update_available("2.9.4")
assert "UPDATE" in top_bar.btn_version_chip.text()
assert "2.9.4" in top_bar.btn_version_chip.toolTip()
print(f"5. set_update_available('2.9.4') updated chip text to: '{top_bar.btn_version_chip.text()}'")

top_bar.set_notification_badge(True)
assert "•" in top_bar.btn_notifications.text()
print(f"6. set_notification_badge(True) updated bell text to: '{top_bar.btn_notifications.text()}'")

top_bar.set_notification_badge(False)
assert top_bar.btn_notifications.text() == "🔔"
print("7. set_notification_badge(False) cleared unread dot.")

# 2. Test UpdateCenterDialog
dlg_update = UpdateCenterDialog()
assert hasattr(dlg_update, "lbl_curr_ver"), "UpdateCenterDialog missing lbl_curr_ver"
assert hasattr(dlg_update, "lbl_status"), "UpdateCenterDialog missing lbl_status"
assert hasattr(dlg_update, "btn_update"), "UpdateCenterDialog missing btn_update"
assert f"v{__version__}" in dlg_update.lbl_curr_ver.text()

# Simulate manifest update available
manifest_update = {
    "version": "2.9.4",
    "latest_version": "2.9.4",
    "download_url": "https://talent-ops-ai.vercel.app/download-scout",
    "release_notes": "Added interactive notifications and fleet update center."
}
dlg_update._apply_manifest_result(manifest_update)
assert dlg_update.btn_update.isEnabled() == True
assert "2.9.4" in dlg_update.btn_update.text()
assert "2.9.4" in dlg_update.lbl_status.text()
print("8. UpdateCenterDialog successfully parsed manifest with newer version and enabled Update action.")

# Simulate manifest up to date
manifest_current = {
    "version": __version__,
    "latest_version": __version__,
    "download_url": "https://talent-ops-ai.vercel.app/download-scout",
    "release_notes": "Up to date."
}
dlg_update._apply_manifest_result(manifest_current)
assert dlg_update.btn_update.isEnabled() == False
assert "Up to Date" in dlg_update.btn_update.text()
assert "up to date" in dlg_update.lbl_status.text().lower()
print("9. UpdateCenterDialog successfully handles 'Up to Date' status when versions match.")

# 3. Test NotificationsDialog
dlg_notif = NotificationsDialog()
sample_items = [
    {
        "id": "notif-1",
        "title": "Fleet Release v2.9.3 Deployed",
        "type": "UPDATE",
        "created_at": "2026-09-22T20:00:00Z",
        "message": "Desktop Scout v2.9.3 is live with company semantic heuristics and update center."
    },
    {
        "id": "notif-2",
        "title": "Cloud Telemetry Synced",
        "type": "SUCCESS",
        "created_at": "2026-09-22T20:10:00Z",
        "message": "Connected to fleet cluster node #483."
    }
]
dlg_notif._render_notifications(sample_items)
assert len(dlg_notif.notifications) == 2
print(f"10. NotificationsDialog successfully rendered {len(dlg_notif.notifications)} notifications with badges.")

# 4. Test MainWindow wiring
main_win = MainWindow()
assert hasattr(main_win, "show_update_center")
assert hasattr(main_win, "show_notifications")

# Verify settings page check_updates_requested connection
settings_clicked = []
main_win.show_update_center = lambda: settings_clicked.append(True)
main_win.page_settings.check_updates_requested.emit()
assert len(settings_clicked) == 1, "Settings page check_updates_requested did not route to show_update_center"
print("11. PageSettings '🔄 Check for updates' successfully routed to MainWindow.show_update_center.")

print("\n>>> CHECK 1 PASSED: Desktop Scout TopBar, Update Center, and Notifications Dialog fully verified!")
