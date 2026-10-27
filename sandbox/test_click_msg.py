import sys
import ctypes
from ctypes import wintypes
import time

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

hwnd = 265910

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

# Convert (799, 569) to lParam
lParam = (569 << 16) | (799 & 0xFFFF)
print("Sending WM_LBUTTONDOWN...")
res1 = user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
time.sleep(0.05)
print("Sending WM_LBUTTONUP...")
res2 = user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
print("Results:", res1, res2)
