import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

from pywinauto import Application

hwnd = 131694
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()

for i, d in enumerate(desc):
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    aid = d.element_info.automation_id or ""
    r = d.rectangle()
    if "just one reply" in txt.lower() or aid == "myInput" or "send" in txt.lower():
        print(f"[{i:02d}] {d.element_info.control_type} | aid='{aid}' | txt='{txt[:60]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
