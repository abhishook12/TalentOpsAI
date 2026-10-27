import sys
import ctypes
from ctypes import wintypes
import time

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32

ensure_interactive_desktop()

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

hwnd = wintypes.HWND(131694)
is_win = user32.IsWindow(hwnd)
print(f"IsWindow(131694): {is_win}")

rect = wintypes.RECT()
ok = user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"GetWindowRect: {ok}, Rect: L={rect.left}, T={rect.top}, R={rect.right}, B={rect.bottom}")

from pywinauto import Application
try:
    app = Application(backend="uia").connect(handle=131694)
    print("pywinauto connect success!")
    win = app.window(handle=131694)
    desc = win.descendants()
    print(f"Descendants: {len(desc)}")
except Exception as e:
    print(f"pywinauto connect failed: {e}")
