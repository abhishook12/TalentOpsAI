import ctypes
import win32gui
import win32process
import psutil

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

print("--- Running Vitel Processes ---")
vitel_pids = []
for p in psutil.process_iter(['pid', 'name']):
    if 'vitel' in p.info['name'].lower() or 'qtwebengine' in p.info['name'].lower():
        print(f"PID: {p.info['pid']} | Name: {p.info['name']}")
        if 'vitelglobal' in p.info['name'].lower():
            vitel_pids.append(p.info['pid'])

print("\n--- Windows for Vitel ---")
def enum_cb(h, _):
    _, pid = win32process.GetWindowThreadProcessId(h)
    if pid in vitel_pids:
        title = win32gui.GetWindowText(h)
        vis = win32gui.IsWindowVisible(h)
        rect = win32gui.GetWindowRect(h)
        cls = win32gui.GetClassName(h)
        print(f"HWND: {h} | Title: '{title}' | Visible: {vis} | Rect: {rect} | Class: {cls}")

win32gui.EnumWindows(enum_cb, None)
