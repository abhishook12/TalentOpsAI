import sys
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
import psutil

ensure_interactive_desktop()

def find_vitel_hwnd():
    # 1. Get all PIDs for Vitelglobal
    vitel_pids = set()
    for p in psutil.process_iter(['pid', 'name']):
        if 'vitel' in (p.info['name'] or '').lower():
            vitel_pids.add(p.info['pid'])
    
    print(f"Vitel PIDs: {vitel_pids}")
    
    found_hwnds = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    
    def enum_cb(h, l):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in vitel_pids:
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, class_buf, 256)
            length = user32.GetWindowTextLengthW(h) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(h, buf, length)
            is_vis = user32.IsWindowVisible(h)
            found_hwnds.append((h, pid.value, buf.value, class_buf.value, is_vis))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    
    # Priority: Visible window with Qt663QWindowIcon or title Vitelglobal
    for h, pid, title, cls, is_vis in found_hwnds:
        print(f"Candidate: HWND={h}, Title='{title}', Class='{cls}', Visible={is_vis}")
        if "Qt663QWindowIcon" in cls and is_vis:
            return h
    for h, pid, title, cls, is_vis in found_hwnds:
        if is_vis:
            return h
    return found_hwnds[0][0] if found_hwnds else None

target_hwnd = find_vitel_hwnd()
print(f"Selected HWND: {target_hwnd}")

if target_hwnd:
    from pywinauto import Application
    app = Application(backend="uia").connect(handle=target_hwnd)
    win = app.window(handle=target_hwnd)
    desc = win.descendants()
    print(f"Total descendants: {len(desc)}")
    for i, d in enumerate(desc):
        ctype = d.element_info.control_type
        aid = d.element_info.automation_id or ""
        txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
        r = d.rectangle()
        if ctype in ["Button", "Edit", "ListItem", "Text"] or aid:
            print(f"[{i:02d}] {ctype:10s} | aid='{aid}' | txt='{txt[:50]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
