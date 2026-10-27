import ctypes
import win32gui
import win32con
import win32api
import win32clipboard
import time
import os
import pyautogui
from PIL import Image

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

hwnd = 329408
prev_fg = win32gui.GetForegroundWindow()
orig_cursor = win32api.GetCursorPos()

message = "Hey please reply , you one reply  means so much to me"
win32clipboard.OpenClipboard()
win32clipboard.EmptyClipboard()
win32clipboard.SetClipboardText(message, win32clipboard.CF_UNICODETEXT)
win32clipboard.CloseClipboard()

print("=== STARTING BATCH DISPATCH TO VITEL CHATS ===")

dispatched = []

try:
    # 1. Maximize Vitel window
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    # Function to dispatch to currently active chat
    def send_to_active():
        # Click input box at (550, 720)
        pyautogui.click(550, 720)
        time.sleep(0.08)
        # Paste and submit
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.08)
        pyautogui.press('enter')
        time.sleep(0.05)
        pyautogui.click(1340, 720)
        time.sleep(0.25)

    # Visible rows Y coordinates (Rows 1 to 8)
    row_ys = [305, 365, 425, 485, 545, 605, 665, 720]

    # Process visible contacts first
    for idx, ry in enumerate(row_ys):
        print(f"Selecting contact row {idx+1} at (200, {ry})...")
        pyautogui.click(200, ry)
        time.sleep(0.2)
        send_to_active()
        dispatched.append(f"Row {idx+1}")
        print(f"Dispatched message to Row {idx+1}!")

    # Scroll down in the sidebar to reveal next contacts
    # Mouse at x=200, y=500
    pyautogui.moveTo(200, 500)
    for scroll_cycle in range(3):
        # Scroll down
        pyautogui.scroll(-500)
        time.sleep(0.3)
        # Process newly visible rows (bottom 4 rows)
        for ry in [545, 605, 665, 720]:
            if len(dispatched) >= 20:
                break
            pyautogui.click(200, ry)
            time.sleep(0.2)
            send_to_active()
            dispatched.append(f"Scroll {scroll_cycle+1} Row Y={ry}")
            print(f"Dispatched message ({len(dispatched)}/20)!")

finally:
    # Immediately restore user's previous window & cursor
    if prev_fg and win32gui.IsWindow(prev_fg):
        win32gui.SetForegroundWindow(prev_fg)
    win32api.SetCursorPos(orig_cursor)

print(f"=== BATCH DISPATCH COMPLETED: {len(dispatched)} CHATS PROCESSED ===")

time.sleep(1.0)

# Capture verification screenshot of Vitel
rect = win32gui.GetWindowRect(hwnd)
w, h = rect[2] - rect[0], rect[3] - rect[1]

import win32ui
hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()
saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
saveDC.SelectObject(saveBitMap)
ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

bmpinfo = saveBitMap.GetInfo()
bmpstr = saveBitMap.GetBitmapBits(True)
im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

artifact_dir = r'C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f'
screenshot_path = os.path.join(artifact_dir, 'screenshot_vitel_batch_sent_verified.png')
im.save(screenshot_path)
print(f"[SCREENSHOT PROOF] Saved Vitel Batch Screenshot: {screenshot_path} ({os.path.getsize(screenshot_path)} bytes)")

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)
win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
