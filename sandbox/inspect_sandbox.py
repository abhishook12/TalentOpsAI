import sys
import ctypes
from ctypes import wintypes
import psutil

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32

ensure_interactive_desktop()

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
found = []

def cb(h, l):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(h) + 1
    buf = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(h, buf, length)
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, cls_buf, 256)
    is_vis = user32.IsWindowVisible(h)
    if buf.value or "python" in cls_buf.value.lower() or "tk" in cls_buf.value.lower():
        found.append((h, pid.value, buf.value, cls_buf.value, is_vis))
    return True

user32.EnumWindows(WNDENUMPROC(cb), 0)
print(f"Total candidate windows: {len(found)}")
for h, p, title, cls, is_vis in found:
    if "sandbox" in title.lower() or "practice" in title.lower() or "tk" in cls.lower():
        print(f"MATCH: HWND={h}, Title='{title}', Class='{cls}', Visible={is_vis}")
