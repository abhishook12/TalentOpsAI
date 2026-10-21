"""
daily_antigravity_routine.py — Autonomous Start-of-Day Antigravity Health & System Routine Trigger
==================================================================================================

Triggers automatically at the start of each day:
1. Boot / User Logon (via autostart_talentops.py & Task Scheduler / Startup folder)
2. Wake-from-sleep / Resume (via backend/talentops_supervisor.py clock jump detection)
3. Scheduled morning task (via Windows Task Scheduler)

Guarantees:
- "At the start of the day only": Tracks last run date in daily_routine_check_state.json.
  Executes once per calendar day. Duplicate calls on the same day are safely skipped.
- Ensures Antigravity desktop application is launched and active.
- Verifies Antigravity language_server / agentapi is responsive.
- Submits the automated routine check prompt into Antigravity via `agentapi new-conversation`.
- Includes full diagnostic logging and manual testing support via --force and --status.
"""

import os
import sys
import json
import time
import socket
import logging
import subprocess
from datetime import datetime

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
STATE_FILE = os.path.join(WORKSPACE_DIR, "backend", "daily_routine_check_state.json")
LOG_FILE = os.path.join(WORKSPACE_DIR, "backend", "daily_routine_check.log")

ANTIGRAVITY_EXE = r"C:\Users\User\AppData\Local\Programs\antigravity\Antigravity.exe"
LANGUAGE_SERVER_EXE = r"C:\Users\User\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"
AGENTAPI_BAT = r"C:\Users\User\.gemini\antigravity\bin\agentapi.bat"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DAILY_ROUTINE] %(message)s",
)
logger = logging.getLogger("DailyAntigravityRoutine")

ROUTINE_CHECK_PROMPT = (
    "Perform the automated start-of-day routine check for TalentOps AI:\n"
    "1. Website & Web Frontend: Verify that the Vite frontend server (http://localhost:5173) is active, "
    "builds cleanly, and all main routes and views load properly.\n"
    "2. Core Systems & APIs: Verify that the FastAPI backend server (http://127.0.0.1:8000/ping, /health) "
    "is healthy and all background daemons and supervisors are running.\n"
    "3. Database & Data Integrity: Check the database tables, candidate records, discovery staging counts, "
    "email intelligence logs, and verify there are no locks, corruption, or failed migrations.\n"
    "4. Autonomous Background Engines: Verify the status of the Engine Immunity Sentinel, WebHarvest crawler, "
    "and Night Sweeper loops.\n"
    "5. Deliverability & Corporate Email Gate: Verify the 5-phase Corporate Email Intelligence Gate and Scout dual-sync status.\n"
    "6. Summary & Report: Provide an executive health checklist and flag any issues or anomalies that require user attention."
)


def get_state() -> dict:
    """Reads current daily routine check state from disk."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading state file {STATE_FILE}: {e}")
    return {}


def save_state(state: dict) -> None:
    """Saves updated daily routine check state to disk."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state file {STATE_FILE}: {e}")


def get_today_str() -> str:
    """Returns local calendar date string YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def has_run_today() -> bool:
    """Checks whether the routine check has already run on today's calendar date."""
    state = get_state()
    today_str = get_today_str()
    return state.get("last_run_date") == today_str and state.get("status") == "SUCCESS"


def is_antigravity_running() -> bool:
    """Checks whether the Antigravity desktop process is currently active."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name")
                if name and name.lower() == "antigravity.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.warning(f"psutil check failed: {e}. Falling back to tasklist...")
        try:
            res = subprocess.run(
                ["tasklist", "/fi", "IMAGENAME eq Antigravity.exe"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "Antigravity.exe" in res.stdout
        except Exception:
            pass
    return False


def launch_antigravity() -> bool:
    """Launches the Antigravity desktop application if not running."""
    if is_antigravity_running():
        logger.info("Antigravity desktop application is already running.")
        return True

    if not os.path.exists(ANTIGRAVITY_EXE):
        logger.error(f"Antigravity executable not found at {ANTIGRAVITY_EXE}")
        return False

    logger.info(f"Launching Antigravity desktop application from {ANTIGRAVITY_EXE}...")
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    try:
        subprocess.Popen(
            [ANTIGRAVITY_EXE],
            cwd=WORKSPACE_DIR,
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
        )
        # Give Antigravity Electron process time to start
        for attempt in range(10):
            time.sleep(1.5)
            if is_antigravity_running():
                logger.info(f"Antigravity desktop process active after {(attempt + 1) * 1.5:.1f}s.")
                return True
        logger.warning("Antigravity process launched, proceeding to readiness probe...")
        return True
    except Exception as e:
        logger.error(f"Failed to launch Antigravity desktop: {e}")
        return False


def is_language_server_ready(timeout_sec: float = 3.0) -> bool:
    """Probes Antigravity language server via agentapi get-conversation-metadata or --help."""
    exe = LANGUAGE_SERVER_EXE if os.path.exists(LANGUAGE_SERVER_EXE) else AGENTAPI_BAT
    try:
        res = subprocess.run(
            [exe, "agentapi", "--help"] if exe == LANGUAGE_SERVER_EXE else [exe, "--help"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=WORKSPACE_DIR,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def trigger_daily_antigravity_routine_check(force: bool = False, source: str = "MANUAL") -> dict:
    """
    Main entry point:
    Checks if today's routine has run. If not (or if force=True):
    1. Launches Antigravity desktop app if needed.
    2. Sends the routine check prompt via agentapi new-conversation.
    3. Persists state so it only runs once at the start of each day.
    """
    today_str = get_today_str()
    state = get_state()
    logger.info(f"Evaluating daily routine check trigger (Source: {source}, Force: {force}, Today: {today_str})")

    if not force and has_run_today():
        last_time = state.get("last_run_timestamp", "earlier today")
        cid = state.get("conversation_id", "N/A")
        logger.info(
            f"Start-of-day routine check ALREADY executed for today ({today_str}) at {last_time} "
            f"(Conversation ID: {cid}). Skipping redundant prompt."
        )
        return {
            "status": "SKIPPED_ALREADY_RUN",
            "date": today_str,
            "last_run_timestamp": last_time,
            "conversation_id": cid,
        }

    # 1. Ensure Antigravity desktop app is open
    launch_antigravity()

    # 2. Probe language server readiness
    ready = False
    for attempt in range(5):
        if is_language_server_ready(timeout_sec=4.0):
            ready = True
            break
        time.sleep(2.0)

    if not ready:
        logger.warning("Language server probe did not respond immediately, attempting new-conversation anyway...")

    # 3. Enter the prompt into Antigravity via agentapi new-conversation
    exe = LANGUAGE_SERVER_EXE if os.path.exists(LANGUAGE_SERVER_EXE) else AGENTAPI_BAT
    title = f"TalentOps AI Start-of-Day Routine Check ({today_str})"
    cmd = [exe, "agentapi", "new-conversation", f"--title={title}", ROUTINE_CHECK_PROMPT] if exe == LANGUAGE_SERVER_EXE else [exe, "new-conversation", f"--title={title}", ROUTINE_CHECK_PROMPT]

    logger.info(f"Dispatching new conversation prompt to Antigravity: title='{title}'...")

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25.0,
            cwd=WORKSPACE_DIR,
            check=False,
        )

        conversation_id = ""
        if res.returncode == 0:
            try:
                data = json.loads(res.stdout)
                conversation_id = data.get("response", {}).get("newConversation", {}).get("conversationId", "")
            except Exception:
                conversation_id = "UNKNOWN_JSON_PARSE"

            logger.info(
                f"SUCCESS: Daily routine check conversation created successfully in Antigravity! "
                f"Conversation ID: {conversation_id}"
            )

            # 4. Save state
            new_state = {
                "last_run_date": today_str,
                "last_run_timestamp": datetime.now().isoformat(),
                "conversation_id": conversation_id,
                "conversation_title": title,
                "trigger_source": source,
                "status": "SUCCESS",
            }
            save_state(new_state)

            return {
                "status": "SUCCESS",
                "date": today_str,
                "conversation_id": conversation_id,
                "title": title,
            }
        else:
            logger.error(f"agentapi new-conversation failed (code {res.returncode}): stdout={res.stdout}, stderr={res.stderr}")
            return {
                "status": "FAILED",
                "error": res.stderr or res.stdout,
                "returncode": res.returncode,
            }

    except Exception as e:
        logger.error(f"Exception during agentapi execution: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "error": str(e),
        }


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    status_check = "--status" in sys.argv

    if status_check:
        current_state = get_state()
        print(f"Current Daily Routine Check State:")
        print(json.dumps(current_state, indent=2))
        print(f"Has run today ({get_today_str()}): {has_run_today()}")
        print(f"Is Antigravity running: {is_antigravity_running()}")
        sys.exit(0)

    source_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "CLI_MANUAL"
    result = trigger_daily_antigravity_routine_check(force=force_run, source=source_arg)
    print(json.dumps(result, indent=2))
