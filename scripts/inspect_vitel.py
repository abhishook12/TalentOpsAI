import sys
import ctypes
from ctypes import wintypes
import time

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
from pywinauto import Application

ensure_interactive_desktop()
hwnd = 131694

SW_SHOWNOACTIVATE = 4
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

rect = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"Rect: L={rect.left}, T={rect.top}, R={rect.right}, B={rect.bottom}")

app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()
print(f"Descendants count: {len(desc)}")
for i, d in enumerate(desc):
    ctype = d.element_info.control_type
    aid = d.element_info.automation_id or ""
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    r = d.rectangle()
    if ctype in ["Button", "Edit", "ListItem", "Text"] or aid:
        print(f"[{i}] {ctype} | aid='{aid}' | txt='{txt[:50]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
