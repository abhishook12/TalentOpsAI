import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import ctypes
from ctypes import wintypes

hwnd = 131694
child_hwnds = []

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def enum_child_cb(h, l):
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, cls_buf, 256)
    length = user32.GetWindowTextLengthW(h) + 1
    buf = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(h, buf, length)
    rect = wintypes.RECT()
    user32.GetWindowRect(h, ctypes.byref(rect))
    child_hwnds.append((h, cls_buf.value, buf.value, (rect.left, rect.top, rect.right, rect.bottom)))
    return True

user32.EnumChildWindows(hwnd, WNDENUMPROC(enum_child_cb), 0)
print(f"Child windows of {hwnd}: {len(child_hwnds)}")
for h, cls, title, r in child_hwnds:
    print(f"Child HWND {h} | Class: '{cls}' | Title: '{title}' | Rect: {r}")
