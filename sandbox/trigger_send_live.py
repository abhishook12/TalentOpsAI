import sys
import os
import time
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

from pywinauto import Application

hwnd = 131694

prev_fg_hwnd = user32.GetForegroundWindow()

# Bring to foreground for 100ms
user32.SetForegroundWindow(hwnd)
time.sleep(0.08)

# Send Enter
VK_RETURN = 0x0D
user32.keybd_event(VK_RETURN, 0, 0, 0)
time.sleep(0.02)
user32.keybd_event(VK_RETURN, 0, 2, 0) # KEYUP
time.sleep(0.1)

# Also click send button directly via mouse_event if needed
# send button is at (1289, 608)
orig_pt = wintypes.POINT()
user32.GetCursorPos(ctypes.byref(orig_pt))
user32.SetCursorPos(1289, 608)
user32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
time.sleep(0.02)
user32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
user32.SetCursorPos(orig_pt.x, orig_pt.y)

time.sleep(0.2)

# Restore previous foreground window immediately
if prev_fg_hwnd:
    user32.SetForegroundWindow(prev_fg_hwnd)

# Now check myInput value
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
desc = win.descendants()

my_input_val = None
for d in desc:
    if d.element_info.automation_id == "myInput":
        try:
            my_input_val = d.iface_value.CurrentValue or ""
        except Exception:
            pass
        break

print(f"myInput length after dispatch: {len(my_input_val) if my_input_val is not None else 'None'}")

# Check bubbles
bubbles = []
for d in desc:
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    if "just one reply" in txt.lower():
        bubbles.append(txt)

print(f"Bubbles matching target: {len(bubbles)}")
for b in bubbles:
    print(f"  -> {b[:70]}...")
