"""
teams_daily_collection_service.py — Autonomous Daily 5-Day Teams Background Collection Engine
=============================================================================================

Implements the user mandate:
- Operates daily across 5 working days (Monday - Friday).
- Runs 100% in the background (off-screen, zero screen stealing or user interruption).
- Operates for the first 2 hours of the day (7,200 seconds maximum window).
- Extracts candidate cards, contact info, and recruiter communications shared by team members.
- Stages records in PostgreSQL (discovery_staging) and auto-promotes to Master Recruiters via universal_funnel.
- Synchronizes DuckDB Parquet and in-memory RecruiterStore for instant frontend availability.
- Integrates seamlessly with start-of-day routines, autostart, and the TalentOps OS supervisor.
"""

import os
import sys
import json
import time
import logging
import threading
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Optional

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

STATE_FILE = os.path.join(WORKSPACE_DIR, "backend", "data", "teams_daily_collection_state.json")
LOG_FILE = os.path.join(WORKSPACE_DIR, "backend", "data", "teams_daily_collection.log")
UPWARD_STATUS_FILE = os.path.join(WORKSPACE_DIR, "teams_extractor", "output", "upward_harvest_status.json")

# Virtual environment python that contains pywinauto
VENV_PYTHON = os.path.join(WORKSPACE_DIR, "teams_extractor", "venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

EXTRACTOR_SCRIPT = os.path.join(WORKSPACE_DIR, "teams_extractor", "deep_upward_extractor.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TeamsDailyCollection] %(message)s"
)
logger = logging.getLogger("talentops.teams_daily_collection")

# Global singleton lock & thread reference
_lock = threading.Lock()
_monitor_thread: Optional[threading.Thread] = None
_active_process: Optional[subprocess.Popen] = None
_active_pid: Optional[int] = None


class TeamsDailyCollectionService:
    """
    Manages the automated 5-day weekday start-of-day 2-hour Teams collection lifecycle.
    """

    WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    DEFAULT_DURATION_SECONDS = 7200  # Exactly 2 hours

    def __init__(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    def is_weekday(self, dt: Optional[datetime] = None) -> bool:
        """Returns True if given datetime (or now) is Monday through Friday (0..4)."""
        if dt is None:
            dt = datetime.now()
        return dt.weekday() in range(0, 5)

    def get_day_name(self, dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.now()
        return self.WEEKDAY_NAMES[dt.weekday()]

    def get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def read_state(self) -> Dict[str, Any]:
        """Loads persistent collection state from disk."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading daily collection state: {e}")
        return {
            "date": self.get_today_str(),
            "day_of_week": self.get_day_name(),
            "is_weekday": self.is_weekday(),
            "status": "IDLE",
            "last_completed_date": None,
            "target_duration_hours": 2.0,
            "target_duration_seconds": self.DEFAULT_DURATION_SECONDS,
            "messages_scanned": 0,
            "candidates_staged": 0,
            "candidates_promoted": 0,
            "last_person_collected": None
        }

    def write_state(self, state: Dict[str, Any]) -> None:
        """Persists collection state to disk atomically."""
        try:
            state["last_updated"] = datetime.now().isoformat()
            temp_path = f"{STATE_FILE}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            if os.path.exists(STATE_FILE):
                os.replace(temp_path, STATE_FILE)
            else:
                os.rename(temp_path, STATE_FILE)
        except Exception as e:
            logger.error(f"Error writing daily collection state: {e}")

    def has_run_today(self) -> bool:
        """Checks if the daily 2-hour collection has already finished on today's calendar date."""
        state = self.read_state()
        today = self.get_today_str()
        return (
            state.get("date") == today
            and state.get("status") in ("COMPLETED", "FINISHED")
        )

    def is_running(self) -> bool:
        """Checks if a collection process is actively executing."""
        global _active_process, _active_pid
        if _active_process is not None:
            if _active_process.poll() is None:
                return True
            else:
                _active_process = None
                _active_pid = None
        return False

    def get_status(self) -> Dict[str, Any]:
        """Provides real-time consolidated status for frontend, API, and verification checks."""
        state = self.read_state()
        today = self.get_today_str()
        is_active = self.is_running()

        # Read live metrics from upward_harvest_status.json if available
        live_upward = {}
        if os.path.exists(UPWARD_STATUS_FILE):
            try:
                with open(UPWARD_STATUS_FILE, "r", encoding="utf-8") as f:
                    live_upward = json.load(f)
            except Exception:
                pass

        elapsed = state.get("elapsed_seconds", 0)
        remaining = state.get("remaining_seconds", 0)
        if is_active and live_upward:
            elapsed = live_upward.get("elapsed_seconds", elapsed)
            remaining = live_upward.get("remaining_seconds", remaining)

        target_sec = state.get("target_duration_seconds") if is_active else self.DEFAULT_DURATION_SECONDS
        if not target_sec or target_sec < 60:
            target_sec = self.DEFAULT_DURATION_SECONDS

        return {
            "service_name": "TeamsDailyCollectionEngine",
            "today": today,
            "day_of_week": self.get_day_name(),
            "is_weekday": self.is_weekday(),
            "is_running": is_active,
            "has_run_today": self.has_run_today(),
            "status": "RUNNING" if is_active else state.get("status", "IDLE"),
            "target_duration_hours": round(target_sec / 3600, 2),
            "target_duration_seconds": target_sec,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "active_pid": _active_pid or state.get("process_pid"),
            "trigger_source": state.get("trigger_source", "MANUAL"),
            "start_time": state.get("start_time"),
            "scheduled_finish_time": state.get("scheduled_finish_time"),
            "messages_scanned": live_upward.get("total_messages_scanned", state.get("messages_scanned", 0)),
            "candidates_staged": live_upward.get("total_new_candidates_staged", state.get("candidates_staged", 0)),
            "candidates_promoted": live_upward.get("cumulative_promoted_to_master_db", state.get("candidates_promoted", 0)),
            "last_person_collected": live_upward.get("last_person_collected_name") or state.get("last_person_collected", "None"),
            "chat_target": "CTV- Phone numbers",
            "window_mode": "offscreen (headless coordinates -9000, -9000)"
        }

    def start_collection(
        self,
        duration_seconds: int = DEFAULT_DURATION_SECONDS,
        force: bool = False,
        source: str = "MANUAL",
        chat: str = "CTV- Phone numbers"
    ) -> Dict[str, Any]:
        """
        Launches the daily Teams collection operation:
        1. Validates weekday (Monday - Friday) unless forced.
        2. Validates idempotency (once per day) unless forced.
        3. Spawns deep_upward_extractor.py in 100% background off-screen mode.
        4. Monitors progress and auto-finalizes when duration finishes.
        """
        global _active_process, _active_pid, _monitor_thread

        with _lock:
            today = self.get_today_str()
            day_name = self.get_day_name()
            is_wkday = self.is_weekday()

            # Weekday check
            if not is_wkday and not force:
                logger.info(f"Skipping daily Teams collection: Today is {day_name} (Weekend). Monday-Friday schedule enforced.")
                return {
                    "status": "SKIPPED_WEEKEND",
                    "reason": f"Today is {day_name}. Daily collection operates 5 working days (Monday - Friday).",
                    "today": today,
                    "day_of_week": day_name,
                    "is_weekday": False
                }

            # Once per day check
            if self.has_run_today() and not force:
                logger.info(f"Skipping daily Teams collection: Already completed for today ({today}).")
                return {
                    "status": "SKIPPED_ALREADY_RUN",
                    "reason": f"Daily collection already completed for today ({today}).",
                    "today": today,
                    "day_of_week": day_name,
                    "is_weekday": True
                }

            # Already running check
            if self.is_running():
                logger.info(f"Daily Teams collection is already actively running (PID {_active_pid}).")
                return {
                    "status": "ALREADY_RUNNING",
                    "active_pid": _active_pid,
                    "today": today,
                    "day_of_week": day_name
                }

            logger.info(
                f"🚀 Dispatching Daily 5-Day Teams Collection: duration={duration_seconds}s ({round(duration_seconds/3600, 2)}h), "
                f"source={source}, chat='{chat}', offscreen=True"
            )

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

            cmd = [
                VENV_PYTHON,
                EXTRACTOR_SCRIPT,
                "--chat", chat,
                "--duration", str(duration_seconds),
                "--delay", "1.8",
                "--offscreen"
            ]

            start_dt = datetime.now()
            scheduled_end_dt = datetime.fromtimestamp(start_dt.timestamp() + duration_seconds)

            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=WORKSPACE_DIR,
                    creationflags=creation_flags,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False
                )
                _active_process = proc
                _active_pid = proc.pid

                initial_state = {
                    "date": today,
                    "day_of_week": day_name,
                    "is_weekday": is_wkday,
                    "status": "RUNNING",
                    "start_time": start_dt.isoformat(),
                    "scheduled_finish_time": scheduled_end_dt.isoformat(),
                    "target_duration_seconds": duration_seconds,
                    "target_duration_hours": round(duration_seconds / 3600, 2),
                    "process_pid": proc.pid,
                    "trigger_source": source,
                    "chat_target": chat,
                    "elapsed_seconds": 0,
                    "remaining_seconds": duration_seconds,
                    "messages_scanned": 0,
                    "candidates_staged": 0,
                    "candidates_promoted": 0,
                    "last_person_collected": None
                }
                self.write_state(initial_state)

                # Launch async watchdog thread to track completion
                def _watchdog_loop():
                    self._monitor_and_finalize(proc, duration_seconds)

                _monitor_thread = threading.Thread(target=_watchdog_loop, daemon=True, name="TeamsDailyWatchdog")
                _monitor_thread.start()

                logger.info(f"✅ Daily Teams Collection launched successfully (PID: {proc.pid})")
                return {
                    "status": "STARTED",
                    "today": today,
                    "day_of_week": day_name,
                    "process_pid": proc.pid,
                    "duration_seconds": duration_seconds,
                    "scheduled_finish": scheduled_end_dt.isoformat(),
                    "trigger_source": source
                }

            except Exception as e:
                logger.error(f"Failed to launch daily Teams collection process: {e}")
                return {
                    "status": "ERROR",
                    "error": str(e)
                }

    def _monitor_and_finalize(self, proc: subprocess.Popen, duration_seconds: int):
        """Monitors the active collection run and runs post-harvest data promotion upon finish."""
        global _active_process, _active_pid
        start_time = time.time()
        logger.info(f"Watchdog monitoring collection process PID {proc.pid} for {duration_seconds}s...")

        while True:
            poll_res = proc.poll()
            elapsed = int(time.time() - start_time)
            remaining = max(0, duration_seconds - elapsed)

            # Read live metrics from upward_harvest_status.json
            live_metrics = {}
            if os.path.exists(UPWARD_STATUS_FILE):
                try:
                    with open(UPWARD_STATUS_FILE, "r", encoding="utf-8") as f:
                        live_metrics = json.load(f)
                except Exception:
                    pass

            # Update running state
            state = self.read_state()
            state["elapsed_seconds"] = elapsed
            state["remaining_seconds"] = remaining
            if live_metrics:
                state["messages_scanned"] = live_metrics.get("total_messages_scanned", state.get("messages_scanned", 0))
                state["candidates_staged"] = live_metrics.get("total_new_candidates_staged", state.get("candidates_staged", 0))
                state["candidates_promoted"] = live_metrics.get("cumulative_promoted_to_master_db", state.get("candidates_promoted", 0))
                state["last_person_collected"] = live_metrics.get("last_person_collected_name") or state.get("last_person_collected")
            self.write_state(state)

            if poll_res is not None or elapsed >= duration_seconds:
                # Process completed or duration reached
                if poll_res is None:
                    # Duration exceeded, terminate process gracefully
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                break

            time.sleep(10)

        logger.info("Daily Teams collection session completed. Running post-harvest synchronization...")
        _active_process = None
        _active_pid = None

        # Execute Post-Harvest Promotion & Dual-Sync
        self._execute_post_harvest_sync()

        # Update final state
        final_state = self.read_state()
        final_state["status"] = "COMPLETED"
        final_state["last_completed_date"] = self.get_today_str()
        final_state["target_duration_seconds"] = self.DEFAULT_DURATION_SECONDS
        final_state["target_duration_hours"] = 2.0
        final_state["remaining_seconds"] = 0
        final_state["completion_timestamp"] = datetime.now().isoformat()
        final_state["process_pid"] = None
        self.write_state(final_state)
        logger.info(f"🏁 Daily Teams Collection for {self.get_today_str()} finalized successfully.")

    def _execute_post_harvest_sync(self):
        """Promotes staged records, normalizes fields, and updates DuckDB Parquet and RecruiterStore."""
        try:
            logger.info("Executing promotion of TEAMS_CTV_UPWARD_STREAM staged records...")
            from teams_extractor.promote_teams_stream import promote_all_teams_stream
            promote_all_teams_stream()
            logger.info("✅ Post-harvest stream promotion & Parquet sync complete.")
        except Exception as e:
            logger.error(f"Post-harvest sync error: {e}")

    def stop_collection(self) -> Dict[str, Any]:
        """Manually stops any running collection session."""
        global _active_process, _active_pid
        if not self.is_running():
            return {"status": "NOT_RUNNING"}

        try:
            if _active_process:
                _active_process.terminate()
                _active_process.wait(timeout=5)
            elif _active_pid:
                import psutil
                p = psutil.Process(_active_pid)
                p.terminate()

            _active_process = None
            _active_pid = None

            state = self.read_state()
            state["status"] = "STOPPED_MANUALLY"
            state["target_duration_seconds"] = self.DEFAULT_DURATION_SECONDS
            state["target_duration_hours"] = 2.0
            state["process_pid"] = None
            self.write_state(state)

            # Run sync
            self._execute_post_harvest_sync()
            return {"status": "STOPPED", "message": "Daily collection stopped and data synchronized."}
        except Exception as e:
            logger.error(f"Error stopping collection: {e}")
            return {"status": "ERROR", "error": str(e)}


# Global singleton instance
teams_daily_service = TeamsDailyCollectionService()
