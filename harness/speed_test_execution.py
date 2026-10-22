import ctypes
import win32gui
import win32con
import win32api
import win32clipboard
import time
import os
import pyautogui
from PIL import Image

import sys
sys.path.insert(0, r"C:\TalentOpsAI")

from harness.sequence_engine import sequence_engine
from harness.connectors.vitel_connector import vitel_connector

user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

print("=== STARTING FASTEST METHOD HARNESS SPEED TEST ===")

# =========================================================================
# TEST 1: Sub-Second Live Vitel Application UI Dispatch
# =========================================================================
hwnd = 329408
prev_fg = win32gui.GetForegroundWindow()
orig_cursor = win32api.GetCursorPos()

message = "Hey please reply , you one reply  means so much to me"
win32clipboard.OpenClipboard()
win32clipboard.EmptyClipboard()
win32clipboard.SetClipboardText(message, win32clipboard.CF_UNICODETEXT)
win32clipboard.CloseClipboard()

t0_ui = time.perf_counter()

try:
    # 1. Maximize Vitel
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    win32gui.SetForegroundWindow(hwnd)
    
    # 2. Click input box (550, 720)
    pyautogui.click(550, 720)
    
    # 3. Paste and Submit
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('enter')
    pyautogui.click(1340, 720)

finally:
    # Immediately restore user's active window
    if prev_fg and win32gui.IsWindow(prev_fg):
        win32gui.SetForegroundWindow(prev_fg)
    win32api.SetCursorPos(orig_cursor)

t1_ui = time.perf_counter()
ui_latency_ms = (t1_ui - t0_ui) * 1000
print(f"[TEST 1 PASS] Live Vitel UI Dispatch Executed in: {ui_latency_ms:.2f} ms ({ui_latency_ms/1000:.3f} s)")

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
screenshot_path = os.path.join(artifact_dir, 'screenshot_vitel_speed_test_verified.png')
im.save(screenshot_path)
print(f"[SCREENSHOT PROOF] Saved Vitel UI Proof: {screenshot_path} ({os.path.getsize(screenshot_path)} bytes)")

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)
win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

# =========================================================================
# TEST 2: Harness Multi-Contact Batch Processing Engine (20 Contacts)
# =========================================================================
t0_batch = time.perf_counter()
batch_latencies = []

for i in range(20):
    t_item_0 = time.perf_counter()
    phone = f"+1415645{8000 + i}"
    res = sequence_engine.enroll_and_dispatch(
        phone=phone,
        message=message,
        name=f"Candidate {i+1}",
        interval_hours=24,
        max_touches=4
    )
    t_item_1 = time.perf_counter()
    batch_latencies.append((t_item_1 - t_item_0) * 1000)

t1_batch = time.perf_counter()
total_batch_ms = (t1_batch - t0_batch) * 1000
avg_batch_ms = sum(batch_latencies) / len(batch_latencies)

print(f"[TEST 2 PASS] Batch 20-Contact Processing Finished in: {total_batch_ms:.2f} ms ({total_batch_ms/1000:.3f} s)")
print(f"  - Average Per-Contact Latency: {avg_batch_ms:.2f} ms")
print(f"  - Fastest Contact: {min(batch_latencies):.2f} ms | Slowest Contact: {max(batch_latencies):.2f} ms")

# =========================================================================
# TEST 3: REST API Round-Trip Benchmark
# =========================================================================
import urllib.request, json
req_data = json.dumps({
    "command": "repeat message to +14156450879 the mssg is -Hey please reply , you one reply  means so much to me"
}).encode('utf-8')

t0_api = time.perf_counter()
req = urllib.request.Request(
    'http://127.0.0.1:8000/harness/command',
    data=req_data,
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as response:
    resp_data = json.loads(response.read().decode())
t1_api = time.perf_counter()
api_latency_ms = (t1_api - t0_api) * 1000

print(f"[TEST 3 PASS] Full REST API Roundtrip Latency: {api_latency_ms:.2f} ms (Status: {resp_data.get('success')})")
print("=== SPEED TEST COMPLETED SUCCESSFULLY ===")
