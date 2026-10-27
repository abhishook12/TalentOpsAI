"""
live_test_19173620345.py — Ultra-Fast Live Dispatcher for Vitel Target 19173620345
===================================================================================
1. Restores Vitel window to ensure it's rendered.
2. Selects / searches 19173620345.
3. Rapidly pastes the exact message with emojis (😃 and 🤝).
4. Submits in sub-second time.
5. Verifies outgoing message in conversation.
6. Restores original foreground window so user's work is undisturbed.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import win32clipboard
from pywinauto import Application

TARGET_NUMBER = "19173620345"
TARGET_MESSAGE = (
    "Hello😃\n\n"
    "Just one reply from you would honestly make my day. "
    "Give me one chance, and I’ll make sure you see the difference. 🤝"
)

# Win32 Constants
SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4
SW_MINIMIZE = 6
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

VK_CONTROL = 0x11
VK_A = 0x41
VK_V = 0x56
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002

def send_key_combination(mod_vk, key_vk):
    user32.keybd_event(mod_vk, 0, 0, 0)
    user32.keybd_event(key_vk, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(key_vk, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(mod_vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

def send_single_key(key_vk):
    user32.keybd_event(key_vk, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(key_vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

def post_click(hwnd, screen_x, screen_y):
    pt = wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    lParam = (pt.y << 16) | (pt.x & 0xFFFF)
    user32.PostMessageW(hwnd, 0x0201, 1, lParam) # WM_LBUTTONDOWN
    time.sleep(0.03)
    user32.PostMessageW(hwnd, 0x0202, 0, lParam) # WM_LBUTTONUP
    time.sleep(0.05)

def main():
    t_start = time.time()
    print("=" * 65)
    print(f"STARTING RAPID DISPATCH TO TARGET: {TARGET_NUMBER}")
    print("=" * 65)

    # 1. Capture user's active window to restore after
    prev_fg_hwnd = user32.GetForegroundWindow()

    # 2. Find Vitel Window
    hwnd = user32.FindWindowW("Qt663QWindowIcon", "Vitelglobal")
    if not hwnd:
        hwnd = user32.FindWindowW(None, "Vitelglobal")
    if not hwnd:
        print("[ERROR] Vitelglobal window not found!")
        sys.exit(1)

    print(f"[INIT] Vitel HWND: {hwnd} | Previous Foreground HWND: {prev_fg_hwnd}")

    # Set clipboard content immediately
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(TARGET_MESSAGE, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    print("[CLIPBOARD] Target payload copied to clipboard.")

    # Connect UIA
    app = Application(backend="uia").connect(handle=hwnd)
    win = app.window(handle=hwnd)

    # Bring window to foreground momentarily for Chromium paste
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.1)

    # Check if 19173620345 is already the active chat
    desc = win.descendants()
    is_already_active = False
    for d in desc:
        r = d.rectangle()
        txt = (d.window_text() or "")
        if TARGET_NUMBER in txt and r.top < 100 and r.left > 400:
            is_already_active = True
            print(f"[FOUND] Target {TARGET_NUMBER} is already active in chat header!")
            break

    # If not active, search for it
    if not is_already_active:
        print(f"[SEARCH] Searching for {TARGET_NUMBER}...")
        # Find search box :r2:
        search_box = None
        for d in desc:
            if d.element_info.automation_id == ":r2:":
                search_box = d
                break
        if search_box:
            r = search_box.rectangle()
            post_click(hwnd, (r.left + r.right) // 2, (r.top + r.bottom) // 2)
            time.sleep(0.05)
            # Type number in search box
            for ch in TARGET_NUMBER:
                user32.PostMessageW(hwnd, 0x0102, ord(ch), 0)
                time.sleep(0.005)
            time.sleep(0.2)
            # Re-read descendants to click search result
            desc = win.descendants()

        # Find target in list
        for d in desc:
            txt = d.window_text() or ""
            r = d.rectangle()
            if TARGET_NUMBER in txt and r.left < 460 and r.top > 150:
                print(f"[CLICK] Clicking target item in list at {r}...")
                post_click(hwnd, (r.left + r.right) // 2, (r.top + r.bottom) // 2)
                time.sleep(0.2)
                break

    # Find myInput
    desc = win.descendants()
    my_input = None
    for d in desc:
        if d.element_info.automation_id == "myInput":
            my_input = d
            break

    if not my_input:
        print("[ERROR] myInput not found!")
        user32.SetForegroundWindow(prev_fg_hwnd)
        sys.exit(1)

    # Click myInput
    r = my_input.rectangle()
    cx = (r.left + r.right) // 2
    cy = (r.top + r.bottom) // 2
    print(f"[FOCUS] Focusing myInput at ({cx}, {cy})...")
    post_click(hwnd, cx, cy)
    time.sleep(0.05)

    # Paste payload via Ctrl+A, Ctrl+V
    print("[PASTE] Sending Ctrl+A, Ctrl+V...")
    send_key_combination(VK_CONTROL, VK_A)
    time.sleep(0.03)
    send_key_combination(VK_CONTROL, VK_V)
    time.sleep(0.05)

    # Trigger Send: Click Send button + VK_RETURN
    send_btn = None
    for d in desc:
        r_b = d.rectangle()
        if d.element_info.control_type == "Button" and r_b.top > 650 and r_b.left > 1300:
            send_btn = d
            break

    if send_btn:
        r_s = send_btn.rectangle()
        print(f"[SEND] Clicking Send button at ({r_s.left}, {r_s.top})...")
        post_click(hwnd, (r_s.left + r_s.right) // 2, (r_s.top + r_s.bottom) // 2)

    send_single_key(VK_RETURN)
    time.sleep(0.3)

    # Restore previous foreground window immediately
    if prev_fg_hwnd and prev_fg_hwnd != hwnd:
        user32.SetForegroundWindow(prev_fg_hwnd)

    elapsed_ms = round((time.time() - t_start) * 1000, 2)
    print(f"[SPEED] Dispatch completed in {elapsed_ms} ms ({elapsed_ms/1000:.2f} s)!")

    # Verify delivery in UI
    time.sleep(0.5)
    desc_post = win.descendants()
    verified = False
    for d in desc_post:
        txt = (d.window_text() or "").encode("ascii", errors="replace").decode("ascii")
        if "Just one reply from you" in txt:
            verified = True
            print(f"[VERIFIED] Delivered message found in conversation: {txt[:60]}...")
            break

    print("=" * 65)
    print(f"STATUS: {'DELIVERED & VERIFIED' if verified else 'DISPATCHED (Pending ACK)'}")
    print(f"TOTAL EXECUTION TIME: {elapsed_ms} ms")
    print("=" * 65)

if __name__ == "__main__":
    main()
