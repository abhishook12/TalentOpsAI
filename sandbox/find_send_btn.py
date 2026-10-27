import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()
from pywinauto import Application

hwnd = 131694
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
for i, d in enumerate(win.descendants()):
    r = d.rectangle()
    if r.top > 500 and r.left > 1200 and d.element_info.control_type == "Button":
        print(f"[{i}] Button rect=({r.left},{r.top},{r.right},{r.bottom}) text='{d.window_text()}'")
