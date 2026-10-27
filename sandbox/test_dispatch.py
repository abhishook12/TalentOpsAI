import sys
import os
# Force utf-8 stdout
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import ctypes
from ctypes import wintypes
import time
import json

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

hwnd = 265910
user32.ShowWindow(hwnd, 4) # SW_SHOWNOACTIVATE
user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010) # HWND_BOTTOM

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D

def post_click(hwnd, screen_x, screen_y):
    pt = wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    lParam = (pt.y << 16) | (pt.x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
    time.sleep(0.02)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
    time.sleep(0.04)

print("1. Clicking input box at (687, 700)...")
post_click(hwnd, 687, 700)
time.sleep(0.1)

test_text = "Test Message \U0001f603 \U0001f91d"
print(f"2. Injecting text length={len(test_text)} via WM_CHAR UTF-16...")
utf16_units = test_text.encode("utf-16-le")
for i in range(0, len(utf16_units), 2):
    code_unit = utf16_units[i] | (utf16_units[i+1] << 8)
    user32.PostMessageW(hwnd, WM_CHAR, code_unit, 0)
    time.sleep(0.005)

time.sleep(0.1)
print("3. Clicking Send button at (907, 700)...")
post_click(hwnd, 907, 700)
time.sleep(0.2)

# Check state file
with open(r"c:\TalentOpsAI\sandbox\mock_chat_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

print(f"Total sent: {state['total_sent']}")
if state['received_logs']:
    last_log = state['received_logs'][-1]
    print(f"Last log target: {last_log['target']}")
    print(f"Last log text: {repr(last_log['text'])}")
else:
    print("No logs yet")
