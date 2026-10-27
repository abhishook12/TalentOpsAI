import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import pywinauto
from pywinauto import Application

hwnd = 131694
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()

for d in desc:
    aid = d.element_info.automation_id or ""
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    r = d.rectangle()
    if aid == "myInput":
        print(f"myInput: rect=({r.left},{r.top},{r.right},{r.bottom}) value='{d.iface_value.CurrentValue if hasattr(d, 'iface_value') and d.iface_value else ''}'")
    elif aid == ":r2:":
        print(f"Search :r2:: rect=({r.left},{r.top},{r.right},{r.bottom})")
    elif d.element_info.control_type == "Button" and r.top > 650 and r.left > 1250:
        print(f"SendBtn candidate: text='{txt}' rect=({r.left},{r.top},{r.right},{r.bottom})")
    elif "19173620345" in txt:
        print(f"Target text in UI: text='{txt}' rect=({r.left},{r.top},{r.right},{r.bottom})")
