import sys
import os
import time
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import pywinauto
from pywinauto import Application

hwnd = 131694

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_BACK = 0x08

def post_click(screen_x, screen_y):
    pt = wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    lParam = (pt.y << 16) | (pt.x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
    time.sleep(0.02)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
    time.sleep(0.04)

app = Application(backend="uia").connect(handle=hwnd)
win = app.window(handle=hwnd)

# Find myInput
my_input = None
for d in win.descendants():
    if d.element_info.automation_id == "myInput":
        my_input = d
        break

if not my_input:
    print("myInput not found!")
    sys.exit(1)

r = my_input.rectangle()
cx = (r.left + r.right) // 2
cy = (r.top + r.bottom) // 2
print(f"Clicking myInput at ({cx}, {cy})...")
post_click(cx, cy)
time.sleep(0.05)

# Clear old text
for _ in range(50):
    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_BACK, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, VK_BACK, 0)

time.sleep(0.05)

test_msg = "Hello\U0001f603\n\nJust one reply from you would honestly make my day. Give me one chance, and I\u2019ll make sure you see the difference. \U0001f91d"

print(f"Injecting test payload ({len(test_msg)} chars)...")
# Send as UTF-16 code units
utf16_units = test_msg.encode("utf-16-le")
for i in range(0, len(utf16_units), 2):
    code_unit = utf16_units[i] | (utf16_units[i+1] << 8)
    user32.PostMessageW(hwnd, WM_CHAR, code_unit, 0)
    time.sleep(0.001)

time.sleep(0.2)

# Read back current value from myInput
val = ""
try:
    val = my_input.iface_value.CurrentValue
    val_clean = val.encode("ascii", errors="replace").decode("ascii")
    print(f"myInput CurrentValue ({len(val)} chars): {val_clean[:60]}...")
except Exception as e:
    print(f"Failed to read CurrentValue: {e}")
