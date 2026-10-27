import sys
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
from pywinauto import Application

ensure_interactive_desktop()
hwnd = 265910

# Test win32 backend
try:
    app_win32 = Application(backend="win32").connect(handle=hwnd)
    win_w32 = app_win32.window(handle=hwnd)
    print("Win32 backend connected successfully!")
    for idx, c in enumerate(win_w32.children()):
        r = c.rectangle()
        print(f"Child [{idx}]: class='{c.class_name()}', text='{c.window_text()}', rect=({r.left},{r.top},{r.right},{r.bottom})")
except Exception as e:
    print("Win32 backend failed:", e)

# Test uia backend
try:
    app_uia = Application(backend="uia").connect(handle=hwnd)
    win_uia = app_uia.window(handle=hwnd)
    print("\nUIA backend connected successfully!")
    desc = win_uia.descendants()
    print(f"UIA Descendants: {len(desc)}")
    for idx, d in enumerate(desc[:15]):
        r = d.rectangle()
        print(f"UIA [{idx}]: type='{d.element_info.control_type}', text='{d.window_text()}', rect=({r.left},{r.top},{r.right},{r.bottom})")
except Exception as e:
    print("UIA backend failed:", e)
