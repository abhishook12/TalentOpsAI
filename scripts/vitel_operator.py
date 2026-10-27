"""
vitel_operator.py — Production-Grade, Sub-Second Operator for Vitel Global
==========================================================================
Eliminates all ad-hoc exploratory scripting. Provides a single, deterministic
CLI pipeline for instant message dispatch and batching with built-in Rule 11 verification.
"""

import sys
import os
import time
import argparse
import json
import ctypes
from ctypes import wintypes
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"c:\TalentOpsAI")
from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
ensure_interactive_desktop()

import win32clipboard
import pywinauto
from pywinauto import Application

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

class VitelOperator:
    def __init__(self):
        self.hwnd = user32.FindWindowW("Qt663QWindowIcon", "Vitelglobal")
        if not self.hwnd:
            self.hwnd = user32.FindWindowW(None, "Vitelglobal")
        if not self.hwnd:
            raise RuntimeError("Vitelglobal window not found. Ensure the app is running.")
        
        self.app = Application(backend="uia").connect(handle=self.hwnd)
        self.win = self.app.window(handle=self.hwnd)

    def post_click(self, screen_x: int, screen_y: int):
        pt = wintypes.POINT(screen_x, screen_y)
        user32.ScreenToClient(self.hwnd, ctypes.byref(pt))
        lParam = (pt.y << 16) | (pt.x & 0xFFFF)
        user32.PostMessageW(self.hwnd, 0x0201, 1, lParam) # WM_LBUTTONDOWN
        time.sleep(0.02)
        user32.PostMessageW(self.hwnd, 0x0202, 0, lParam) # WM_LBUTTONUP
        time.sleep(0.03)

    def send_keys(self, mod_vk: int, key_vk: int):
        user32.keybd_event(mod_vk, 0, 0, 0)
        user32.keybd_event(key_vk, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(key_vk, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(mod_vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)

    def send_single_key(self, key_vk: int):
        user32.keybd_event(key_vk, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(key_vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)

    def set_clipboard(self, text: str):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()

    def get_elements_map(self):
        desc = self.win.descendants()
        mapping = {"myInput": None, "search": None, "send": None, "drawer": None}
        for d in desc:
            aid = d.element_info.automation_id or ""
            txt = (d.window_text() or "").lower()
            ctype = d.element_info.control_type
            r = d.rectangle()

            if aid == "myInput":
                mapping["myInput"] = d
            elif aid == ":r2:":
                mapping["search"] = d
            elif "open drawer" in txt and ctype == "Button":
                mapping["drawer"] = d

        # Compute Send Button relative to myInput if not found explicitly
        if mapping["myInput"]:
            r = mapping["myInput"].rectangle()
            # Find the button immediately to the right of myInput
            for d in desc:
                r_b = d.rectangle()
                if d.element_info.control_type == "Button" and r_b.left >= r.right and abs(r_b.top - r.top) < 100:
                    mapping["send"] = d
                    break
        return mapping

    def dispatch_message(self, message: str, target: str = None) -> dict:
        t_start = time.time()
        prev_fg = user32.GetForegroundWindow()

        # 1. Un-minimize if needed
        if user32.IsIconic(self.hwnd):
            user32.ShowWindow(self.hwnd, SW_RESTORE)
            time.sleep(0.1)

        # 2. Get elements map
        elements = self.get_elements_map()
        my_input = elements["myInput"]
        if not my_input:
            return {"success": False, "error": "myInput field not detected"}

        # 3. Copy text to clipboard
        self.set_clipboard(message)

        # 4. Focus Vitel window momentarily
        user32.SetForegroundWindow(self.hwnd)
        time.sleep(0.06)

        # 5. Click myInput
        r = my_input.rectangle()
        cx = (r.left + r.right) // 2
        cy = (r.top + r.bottom) // 2
        self.post_click(cx, cy)
        time.sleep(0.04)

        # 6. Paste: Ctrl+A, Ctrl+V
        self.send_keys(VK_CONTROL, VK_A)
        self.send_keys(VK_CONTROL, VK_V)
        time.sleep(0.04)

        # 7. Trigger Send
        send_btn = elements.get("send")
        if send_btn:
            r_s = send_btn.rectangle()
            self.post_click((r_s.left + r_s.right) // 2, (r_s.top + r_s.bottom) // 2)
        else:
            # Fallback relative coordinates
            self.post_click(r.right + 40, cy)

        self.send_single_key(VK_RETURN)
        time.sleep(0.1)

        # 8. Restore user's foreground window
        if prev_fg and prev_fg != self.hwnd:
            user32.SetForegroundWindow(prev_fg)

        elapsed_ms = round((time.time() - t_start) * 1000, 2)

        # 9. Triple-Check Verification
        time.sleep(0.3)
        desc = self.win.descendants()

        input_cleared = False
        for d in desc:
            if d.element_info.automation_id == "myInput":
                val = d.iface_value.CurrentValue or ""
                input_cleared = (len(val.strip()) == 0)
                break

        bubble_verified = any(message[:25].lower() in (d.window_text() or "").lower() for d in desc)

        return {
            "success": input_cleared and bubble_verified,
            "target": target or "active_chat",
            "elapsed_ms": elapsed_ms,
            "verification": {
                "check1_bubble_delivered": bubble_verified,
                "check2_input_cleared": input_cleared,
                "check3_timing_sla_met": elapsed_ms < 3000
            }
        }

def main():
    parser = argparse.ArgumentParser(description="Vitel Global High-Speed Operator")
    parser.add_argument("--message", type=str, required=True, help="Message payload to transmit")
    parser.add_argument("--target", type=str, help="Target phone number")
    args = parser.parse_args()

    operator = VitelOperator()
    result = operator.dispatch_message(args.message, args.target)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
