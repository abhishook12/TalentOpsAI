import sys
import ctypes
from ctypes import wintypes
import time
import psutil

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
from pywinauto import Application

ensure_interactive_desktop()

def get_vitel_hwnd():
    vitel_pids = set()
    for p in psutil.process_iter(['pid', 'name']):
        if 'vitel' in (p.info['name'] or '').lower():
            vitel_pids.add(p.info['pid'])
    
    found_hwnds = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    
    def enum_cb(h, l):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in vitel_pids:
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, class_buf, 256)
            is_vis = user32.IsWindowVisible(h)
            if "Qt663QWindowIcon" in class_buf.value and is_vis:
                found_hwnds.append(h)
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return found_hwnds[0] if found_hwnds else None

hwnd = get_vitel_hwnd()
print(f"HWND: {hwnd}")

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

def post_click(hwnd, x, y):
    pt = wintypes.POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    lParam = (pt.y << 16) | (pt.x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
    time.sleep(0.04)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
    time.sleep(0.1)

app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()

drawer_btn = None
for d in desc:
    if d.element_info.control_type == "Button" and "open drawer" in (d.window_text() or "").lower():
        r = d.rectangle()
        if r.top < 200:
            drawer_btn = d
            break

if drawer_btn:
    r = drawer_btn.rectangle()
    cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
    print(f"Clicking top open drawer button at ({cx}, {cy})...")
    post_click(hwnd, cx, cy)
    time.sleep(0.5)

desc2 = win.descendants()
print(f"Descendants count after clicking open drawer: {len(desc2)}")
chat_items = []
for i, d in enumerate(desc2):
    ctype = d.element_info.control_type
    aid = d.element_info.automation_id or ""
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    r = d.rectangle()
    if ctype in ["Button", "ListItem", "Text"] and any(num in txt for num in ["1516", "1414", "1262", "1145", "1801", "1972", "1860", "1646"]):
        print(f"Chat found: [{i:02d}] {ctype} | aid='{aid}' | txt='{txt[:50]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
