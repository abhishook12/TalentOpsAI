"""
chrome_tab_refresher.py — Autonomous Daily Chrome Tab Wakeup & Refresh Service
==============================================================================

Implements the user mandate:
- Operates automatically at the start of each day ("JUST ONCE").
- Discovers all active Google Chrome windows open on screen.
- Iterates through every tab in each Chrome window one by one.
- Selects and refreshes each tab so dormant/discarded tabs wake up and load fresh content.
- Preserves user workflow by restoring the originally focused tab in each window.
- Persists daily state in `backend/data/chrome_tabs_refresh_state.json` to prevent unwanted re-runs.
- Integrates seamlessly with start-of-day autostart, OS supervisor, and Antigravity routines.
"""

import os
import sys
import json
import time
import ctypes
import ctypes.wintypes
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("talentops.chrome_tab_refresher")

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STATE_FILE = os.path.join(WORKSPACE_DIR, "backend", "data", "chrome_tabs_refresh_state.json")

VK_F5 = 0x74
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.wintypes.LPARAM]
user32.EnumWindows.restype = ctypes.wintypes.BOOL


class ChromeTabRefresherService:
    """
    Manages the daily one-time wakeup and refresh routine for all Google Chrome tabs.
    """

    def __init__(self):
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    def get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def read_state(self) -> Dict[str, Any]:
        """Loads state from disk."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading chrome refresh state: {e}")
        return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        """Saves state to disk."""
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving chrome refresh state: {e}")

    def has_run_today(self) -> bool:
        """Checks if the Chrome tab refresh routine has already completed today."""
        state = self.read_state()
        today = self.get_today_str()
        return state.get("date") == today and state.get("status") == "COMPLETED"

    def _trigger_keybd_f5(self):
        """Sends F5 key event to active window as a robust fallback."""
        try:
            user32.keybd_event(VK_F5, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_F5, 0, KEYEVENTF_KEYUP, 0)
        except Exception as e:
            logger.debug(f"keybd_event F5 note: {e}")

    def _execute_refresh_worker(self, result_container: Dict[str, Any], tab_delay_sec: float = 0.8):
        """
        Worker executed on a clean worker thread attached to the interactive 'Default' desktop.
        """
        # 1. Attach to interactive desktop
        h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_default:
            user32.SetThreadDesktop(h_default)
            user32.CloseDesktop(h_default)

        # 2. Initialize COM and UIAutomation
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()

        try:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import (
                CUIAutomation,
                IUIAutomation,
                TreeScope_Descendants,
                UIA_TabItemControlTypeId,
                UIA_ControlTypePropertyId,
                UIA_SelectionItemPatternId,
                IUIAutomationSelectionItemPattern,
                UIA_InvokePatternId,
                IUIAutomationInvokePattern,
                UIA_ButtonControlTypeId,
            )

            uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)

            # 3. Discover all visible Chrome windows
            chrome_windows = []

            def enum_cb(hwnd, lparam):
                class_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buff, 256)
                if class_buff.value == "Chrome_WidgetWin_1":
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        is_vis = user32.IsWindowVisible(hwnd)
                        if is_vis and "Chrome" in buff.value:
                            chrome_windows.append((hwnd, buff.value))
                return True

            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

            total_tabs_refreshed = 0
            tab_cond = uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_TabItemControlTypeId)
            btn_cond = uia.CreatePropertyCondition(UIA_ControlTypePropertyId, UIA_ButtonControlTypeId)
            window_details = []

            for hwnd, win_title in chrome_windows:
                try:
                    elem = uia.ElementFromHandle(hwnd)
                    if not elem:
                        continue

                    tabs = elem.FindAll(TreeScope_Descendants, tab_cond)
                    tab_count = tabs.Length if tabs else 0
                    if tab_count == 0:
                        continue

                    # Look for toolbar reload button
                    btns = elem.FindAll(TreeScope_Descendants, btn_cond)
                    reload_invoker = None
                    if btns:
                        for b_idx in range(btns.Length):
                            b = btns.GetElement(b_idx)
                            b_name = (b.CurrentName or "").strip().lower()
                            if b_name in ("reload", "reload this page", "refresh"):
                                inv = b.GetCurrentPattern(UIA_InvokePatternId)
                                if inv:
                                    reload_invoker = inv.QueryInterface(IUIAutomationInvokePattern)
                                    break

                    # Record original active tab to restore later
                    original_selected_idx = 0
                    tab_elements = []
                    tab_names = []

                    for t_idx in range(tab_count):
                        tab_el = tabs.GetElement(t_idx)
                        tab_elements.append(tab_el)
                        t_name = tab_el.CurrentName or f"Tab {t_idx+1}"
                        tab_names.append(t_name)
                        sel_pat = tab_el.GetCurrentPattern(UIA_SelectionItemPatternId)
                        if sel_pat:
                            sel_it = sel_pat.QueryInterface(IUIAutomationSelectionItemPattern)
                            if sel_it.CurrentIsSelected:
                                original_selected_idx = t_idx

                    logger.info(
                        f"Refreshing Chrome window [HWND={hwnd}] '{win_title}' ({tab_count} tabs, original active: #{original_selected_idx+1})..."
                    )

                    refreshed_in_window = 0
                    # Iterate through tabs one by one
                    for t_idx, tab_el in enumerate(tab_elements):
                        try:
                            sel_pat = tab_el.GetCurrentPattern(UIA_SelectionItemPatternId)
                            if sel_pat:
                                sel_it = sel_pat.QueryInterface(IUIAutomationSelectionItemPattern)
                                sel_it.Select()
                                time.sleep(0.35)  # Allow tab focus switch

                            # Trigger reload
                            if reload_invoker:
                                try:
                                    reload_invoker.Invoke()
                                except Exception:
                                    self._trigger_keybd_f5()
                            else:
                                self._trigger_keybd_f5()

                            refreshed_in_window += 1
                            total_tabs_refreshed += 1
                            time.sleep(tab_delay_sec)
                        except Exception as t_err:
                            logger.warning(f"Error refreshing tab {t_idx+1} in window {hwnd}: {t_err}")

                    # Restore originally selected tab
                    try:
                        if original_selected_idx < len(tab_elements):
                            orig_tab = tab_elements[original_selected_idx]
                            orig_pat = orig_tab.GetCurrentPattern(UIA_SelectionItemPatternId)
                            if orig_pat:
                                orig_it = orig_pat.QueryInterface(IUIAutomationSelectionItemPattern)
                                orig_it.Select()
                    except Exception as r_err:
                        logger.debug(f"Note restoring original tab: {r_err}")

                    window_details.append({
                        "hwnd": hwnd,
                        "title": win_title,
                        "tabs_count": tab_count,
                        "refreshed_count": refreshed_in_window,
                        "tabs": tab_names,
                    })

                except Exception as w_err:
                    logger.warning(f"Error processing Chrome window {hwnd}: {w_err}")

            result_container["status"] = "COMPLETED"
            result_container["windows_scanned"] = len(chrome_windows)
            result_container["tabs_refreshed"] = total_tabs_refreshed
            result_container["window_details"] = window_details

        except Exception as e:
            logger.error(f"Fatal error in Chrome tab refresh worker: {e}", exc_info=True)
            result_container["status"] = "FAILED"
            result_container["error"] = str(e)
        finally:
            comtypes.CoUninitialize()

    def refresh_all_tabs(
        self,
        force: bool = False,
        source: str = "MANUAL",
        tab_delay_sec: float = 0.8
    ) -> Dict[str, Any]:
        """
        Refreshes all tabs across all open Chrome windows.
        If force=False and it has already run today, skips automatically ("JUST ONCE" per day).
        """
        with self._lock:
            today = self.get_today_str()
            if not force and self.has_run_today():
                state = self.read_state()
                logger.info(f"Chrome tab refresh already executed for today ({today}). Skipping redundant run.")
                return {
                    "status": "SKIPPED_ALREADY_RUN",
                    "today": today,
                    "message": "Routine already completed today. Use force=True to re-run.",
                    "last_run": state,
                }

            start_t = time.time()
            logger.info(f"Starting daily Chrome tabs refresh (Source: {source}, Force: {force})...")

            result_container: Dict[str, Any] = {
                "date": today,
                "timestamp": datetime.now().isoformat(),
                "trigger_source": source,
                "status": "RUNNING",
                "windows_scanned": 0,
                "tabs_refreshed": 0,
                "window_details": [],
            }

            worker_thread = threading.Thread(
                target=self._execute_refresh_worker,
                args=(result_container, tab_delay_sec),
                daemon=True,
                name="ChromeTabRefreshWorker"
            )
            worker_thread.start()
            worker_thread.join(timeout=300.0)  # Max 5 minutes for full tab refresh across all windows

            duration = round(time.time() - start_t, 2)
            result_container["duration_seconds"] = duration

            # Save state
            self.save_state(result_container)
            logger.info(
                f"Chrome tab refresh finished with status '{result_container.get('status')}' "
                f"({result_container.get('tabs_refreshed')} tabs in {result_container.get('windows_scanned')} windows in {duration}s)"
            )
            return result_container


# Global singleton instance
chrome_tab_refresher = ChromeTabRefresherService()


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    res = chrome_tab_refresher.refresh_all_tabs(force=force_run, source="CLI_INVOCATION", tab_delay_sec=0.5)
    print(json.dumps(res, indent=2))
