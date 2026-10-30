import ctypes
import sys
import time
import win32gui
import win32con
from pywinauto import Application

sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

top_hwnd = 263026
w0 = win32gui.FindWindowEx(top_hwnd, 0, "Chrome_WidgetWin_0", None)
w1 = win32gui.FindWindowEx(w0, 0, "Chrome_WidgetWin_1", None)
render_hwnd = win32gui.FindWindowEx(w1, 0, "Chrome_RenderWidgetHostHWND", None)
print(f"Render HWND: {render_hwnd}")

app = Application(backend='uia').connect(handle=top_hwnd)
win = app.window(handle=top_hwnd)
before_ids = [d.element_info.automation_id for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]
print(f"Before: {len(before_ids)} messages. Oldest: {before_ids[0]}, Newest: {before_ids[-1]}")

# Test 1: MOUSEWHEEL at (450, 400)
# In Win32 WM_MOUSEWHEEL, positive delta = scroll UP
amount = 120 * 10
x = 450
y = 400
wparam = (amount & 0xFFFF) << 16
lparam = (y << 16) | (x & 0xFFFF)

for _ in range(15):
    win32gui.PostMessage(render_hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)
    time.sleep(0.05)

# Test 2: Also post VK_PRIOR (Page Up) to render_hwnd
win32gui.PostMessage(render_hwnd, win32con.WM_KEYDOWN, win32con.VK_PRIOR, 0)
win32gui.PostMessage(render_hwnd, win32con.WM_KEYUP, win32con.VK_PRIOR, 0)

time.sleep(2.5)

after_ids = [d.element_info.automation_id for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]
print(f"After: {len(after_ids)} messages. Oldest: {after_ids[0]}, Newest: {after_ids[-1]}")
new_older = set(after_ids) - set(before_ids)
print(f"New messages loaded: {len(new_older)}")
for mid in list(new_older)[:5]:
    print("  -> New message ID:", mid)
