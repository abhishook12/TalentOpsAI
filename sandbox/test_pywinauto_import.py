import sys
sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
# Call BEFORE importing pywinauto!
ensure_interactive_desktop()

import pywinauto
from pywinauto import win32functions

hwnd = 265910
print(f"ctypes IsWindow: {user32.IsWindow(hwnd)}")
print(f"pywinauto IsWindow: {win32functions.IsWindow(hwnd)}")

try:
    app = pywinauto.Application(backend="win32").connect(handle=hwnd)
    print("Success connecting with pywinauto!")
except Exception as e:
    print(f"Connect failed: {e}")
