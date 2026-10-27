"""
fast_chat_dispatcher.py — High-Speed Automated Chat Dispatcher (Practice & Benchmark)
====================================================================================
Simulates rapid-fire background messaging across top 20 chat threads:
1. Copies target text payload with emojis (😃 and 🤝).
2. Selects chat 1 -> Pastes/Injects -> Dispatches -> Verifies.
3. Selects chat 2 -> Pastes/Injects -> Dispatches -> Verifies.
4. Extends across all top 20 chats sequentially at maximum throughput.
5. Verifies 0 screen disturbance (user's mouse cursor & foreground window unchanged).
"""

import sys
import os
import time
import json
import ctypes
from ctypes import wintypes
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_MESSAGE = (
    "Hello\U0001f603\n\n"
    "Just one reply from you would honestly make my day. "
    "Give me one chance, and I’ll make sure you see the difference. \U0001f91d"
)

HTML_PATH = Path(r"c:\TalentOpsAI\sandbox\chat_portal.html").resolve().as_uri()

user32 = ctypes.windll.user32

def get_mouse_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

def get_active_window():
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buf = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buf, length)
    return hwnd, buf.value

def run_dispatch(max_chats: int = 20, mode_name: str = "Batch Dispatch"):
    print(f"\n{'='*70}")
    print(f"RUNNING: {mode_name} (Target: {max_chats} chats)")
    print(f"{'='*70}")

    initial_mouse = get_mouse_pos()
    initial_hwnd, initial_title = get_active_window()
    print(f"[PRE-CHECK] Active Foreground Window : HWND {initial_hwnd} ('{initial_title[:40]}')")
    print(f"[PRE-CHECK] Mouse Cursor Position    : {initial_mouse}")
    print(f"[PAYLOAD]   Target Message Length    : {len(TARGET_MESSAGE)} chars (Includes \U0001f603 and \U0001f91d)")

    results = []
    t_start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        page.goto(HTML_PATH)
        page.wait_for_selector("#chat-list")

        for idx in range(max_chats):
            t0 = time.time()
            chat_selector = f"#chat-item-{idx}"

            # 1. Switch to chat
            page.click(chat_selector)

            # 2. Focus input and inject text (simulating clipboard paste)
            page.fill("#myInput", TARGET_MESSAGE)

            # 3. Trigger Send (Enter key or Send button)
            page.click("#sendBtn")

            # 4. Read back active conversation messages to verify delivery
            bubbles = page.query_selector_all(".msg-bubble.sent")
            last_text = bubbles[-1].inner_text() if bubbles else ""

            elapsed_ms = round((time.time() - t0) * 1000, 2)
            has_smiley = "\U0001f603" in last_text
            has_handshake = "\U0001f91d" in last_text
            is_valid = has_smiley and has_handshake and "Just one reply from you" in last_text

            res = {
                "chat_index": idx + 1,
                "elapsed_ms": elapsed_ms,
                "delivered": is_valid,
                "has_emojis": has_smiley and has_handshake,
                "text_snippet": last_text.replace("\n", " ")[:45]
            }
            results.append(res)
            print(f"  -> [Chat {idx+1:02d}] Sent in {elapsed_ms:6.2f}ms | Verified: {is_valid} | Emojis: \U0001f603 \U0001f91d")

        # Extract full state from page
        final_state = page.evaluate("() => window.__chatState")
        browser.close()

    total_time_ms = round((time.time() - t_start) * 1000, 2)
    post_mouse = get_mouse_pos()
    post_hwnd, post_title = get_active_window()

    mouse_drift = abs(post_mouse[0] - initial_mouse[0]) + abs(post_mouse[1] - initial_mouse[1])
    focus_stolen = post_hwnd != initial_hwnd

    print(f"\n{'-'*70}")
    print(f"[SUMMARY] Total Dispatched : {final_state['totalDispatched']}/{max_chats}")
    print(f"[SUMMARY] Total Elapsed    : {total_time_ms:.2f}ms (Average: {total_time_ms/max_chats:.2f}ms/chat)")
    print(f"[SUMMARY] Focus Integrity  : {'PRESERVED' if not focus_stolen else 'FOCUS STOLEN'}")
    print(f"[SUMMARY] Mouse Integrity  : {mouse_drift}px drift (0 = perfectly stationary)")
    print(f"{'='*70}\n")

    return {
        "mode": mode_name,
        "max_chats": max_chats,
        "total_dispatched": final_state['totalDispatched'],
        "total_time_ms": total_time_ms,
        "avg_ms_per_chat": round(total_time_ms / max_chats, 2),
        "focus_preserved": not focus_stolen,
        "mouse_drift_px": mouse_drift,
        "all_delivered": all(r["delivered"] for r in results),
        "results": results
    }

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "first2"
    if mode == "first2":
        run_dispatch(max_chats=2, mode_name="Practice Test 1: First 2 Chats (Copy & Paste)")
    elif mode == "top20":
        run_dispatch(max_chats=20, mode_name="Practice Test 2: Full Top 20 Chats Rapid Dispatch")
    else:
        run_dispatch(max_chats=int(mode), mode_name=f"Practice Test: Top {mode} Chats")
