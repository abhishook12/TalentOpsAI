import sys
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32

ensure_interactive_desktop()

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

hwnds = []

def enum_windows_callback(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 15660:
        length = user32.GetWindowTextLengthW(hwnd) + 1
        title_buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, title_buf, length)
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        is_visible = user32.IsWindowVisible(hwnd)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        hwnds.append((hwnd, pid.value, title_buf.value, class_buf.value, is_visible, (rect.left, rect.top, rect.right, rect.bottom)))
    return True

user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

print(f"Current windows for PID 15660:")
for h, p, title, cls, vis, r in hwnds:
    print(f"HWND: {h} (hex: {hex(h)}) | Title: '{title}' | Class: '{cls}' | Visible: {vis} | Rect: {r}")
