import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import ctypes
from ctypes import wintypes
import time

hwnd = 131694
SW_SHOWNOACTIVATE = 4
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

# Restore without activating, keep at bottom
user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
time.sleep(0.1)

rect = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"Restored Window Rect: L={rect.left}, T={rect.top}, R={rect.right}, B={rect.bottom}")
print(f"IsIconic (Minimized): {user32.IsIconic(hwnd)}")
