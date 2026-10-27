import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import ctypes
from ctypes import wintypes
import psutil
import pywinauto
from pywinauto import Application

vitel_pids = {p.info['pid'] for p in psutil.process_iter(['pid', 'name']) if 'vitel' in (p.info['name'] or '').lower()}
found_hwnds = []
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def enum_cb(h, l):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value in vitel_pids and user32.IsWindowVisible(h):
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, class_buf, 256)
        if "Qt663QWindowIcon" in class_buf.value:
            found_hwnds.append(h)
    return True

user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
hwnd = found_hwnds[0] if found_hwnds else None
print(f"Vitel HWND: {hwnd}")

if hwnd:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print(f"Window Rect: ({rect.left}, {rect.top}, {rect.right}, {rect.bottom})")
    
    app = Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)
    desc = win.descendants()
    print(f"Descendants count: {len(desc)}")
    for i, d in enumerate(desc):
        ctype = d.element_info.control_type
        aid = d.element_info.automation_id or ""
        txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
        r = d.rectangle()
        if ctype in ["Button", "Edit", "Text", "ListItem"] or "search" in aid.lower() or "input" in aid.lower() or "drawer" in txt.lower():
            print(f"[{i:02d}] {ctype:10s} | aid='{aid}' | txt='{txt[:45]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
