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

# Click Send button at dynamic center
app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)
send_btn = None
for d in win.descendants():
    r = d.rectangle()
    if d.element_info.control_type == "Button" and r.left > 1250 and r.top > 550 and r.top < 650:
        send_btn = d
        break

if not send_btn:
    print("Send button not found!")
    sys.exit(1)

r = send_btn.rectangle()
cx = (r.left + r.right) // 2
cy = (r.top + r.bottom) // 2
print(f"Clicking Send button at ({cx}, {cy})...")

pt = wintypes.POINT(cx, cy)
user32.ScreenToClient(hwnd, ctypes.byref(pt))
lParam = (pt.y << 16) | (pt.x & 0xFFFF)
user32.PostMessageW(hwnd, 0x0201, 1, lParam) # WM_LBUTTONDOWN
time.sleep(0.04)
user32.PostMessageW(hwnd, 0x0202, 0, lParam) # WM_LBUTTONUP
time.sleep(0.5)

# Verify myInput value
desc = win.descendants()
for d in desc:
    if d.element_info.automation_id == "myInput":
        val = ""
        try:
            val = d.iface_value.CurrentValue or ""
        except Exception:
            pass
        print(f"myInput value after click ({len(val)} chars): '{val}'")
        break

# Look for outgoing message bubble
for d in desc:
    txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
    if "just one reply" in txt.lower():
        r = d.rectangle()
        print(f"Delivered bubble: '{txt[:60]}...' at {r}")
