import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import pywinauto
from pywinauto import Application

hwnd = 265910
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()
print(f"Descendants count: {len(desc)}")
for idx, d in enumerate(desc[:30]):
    ctype = d.element_info.control_type
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    r = d.rectangle()
    print(f"[{idx:02d}] {ctype:12s} | txt='{txt[:45]}' | rect=({r.left},{r.top},{r.right},{r.bottom})")
