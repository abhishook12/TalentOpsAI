import ctypes
import sys
import re
from pywinauto import Application

sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

top_hwnd = 263026
app = Application(backend='uia').connect(handle=top_hwnd)
win = app.window(handle=top_hwnd)

# Find message bodies matching the ones in the screenshot
target_names = ['ramadan', 'nikki', 'ross', 'heather']
found = []

for d in win.descendants():
    aid = d.element_info.automation_id or ''
    if aid.startswith('message-body-'):
        header = d.element_info.name or ''
        if any(t in header.lower() for t in target_names):
            contents = [c for c in d.children() if (c.element_info.automation_id or '').startswith('content-')]
            tokens = []
            if contents:
                tokens = [ch.element_info.name.strip() for ch in contents[0].children() if ch.element_info.name and ch.element_info.name.strip()]
            found.append({
                'id': aid,
                'header': header,
                'tokens': tokens
            })

print(f"Found {len(found)} matching screenshot messages in live Teams DOM:")
for f in found:
    print(f"\n=== {f['id']} ===")
    print("Header:", f['header'][:150])
    print("Tokens:", f['tokens'])
