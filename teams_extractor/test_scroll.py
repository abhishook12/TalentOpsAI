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

# Find the Chrome_RenderWidgetHostHWND child window
chrome_hwnds = []
def enum_cb(h, _):
    if win32gui.GetClassName(h) == 'Chrome_RenderWidgetHostHWND':
        chrome_hwnds.append(h)
    return True

try:
    win32gui.EnumWindows(enum_cb, None)
except Exception:
    pass
# Or find child of Teams
def enum_child(h, _):
    if win32gui.GetClassName(h) == 'Chrome_RenderWidgetHostHWND':
        chrome_hwnds.append(h)
    return True

try:
    win32gui.EnumChildWindows(263026, enum_child, None)
except:
    pass

# Also check WindowFromPoint
wp_hwnd = win32gui.WindowFromPoint((500, 350))
print(f"WindowFromPoint((500, 350)): HWND={wp_hwnd}, Class={win32gui.GetClassName(wp_hwnd)}")

app = Application(backend='uia').connect(handle=263026)
win = app.window(handle=263026)
before_ids = [d.element_info.automation_id for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]
print(f"Before scroll: {len(before_ids)} messages visible. Oldest: {before_ids[0]}")

# Send WM_MOUSEWHEEL positive (scroll UPWARDS into past)
# Send 5 wheel notches (120 * 5 = 600)
scroll_target = wp_hwnd if win32gui.GetClassName(wp_hwnd) == 'Chrome_RenderWidgetHostHWND' else 263026
amount = 120 * 5  # positive scrolls UP
x = 500
y = 350
wparam = (amount & 0xFFFF) << 16
lparam = (y << 16) | (x & 0xFFFF)

print(f"Posting WM_MOUSEWHEEL to HWND {scroll_target}...")
for _ in range(5):
    win32gui.PostMessage(scroll_target, win32con.WM_MOUSEWHEEL, wparam, lparam)
    time.sleep(0.1)

time.sleep(1.5)

after_ids = [d.element_info.automation_id for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]
print(f"After scroll: {len(after_ids)} messages visible. Oldest: {after_ids[0]}")

new_older = set(after_ids) - set(before_ids)
print(f"New older messages loaded into view: {len(new_older)}")
for mid in list(new_older)[:5]:
    print("  -> New message:", mid)
