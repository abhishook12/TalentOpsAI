"""
autostart_talentops.py — Autonomous Automated Activation Trigger
Executed automatically at:
1. Windows Boot / User Logon
2. Scheduled 6:00 PM IST (Monday to Friday)
Ensures supervisor, backend, and frontend are running, and opens the browser.
"""

import os
import sys
import time
import socket
import logging
import subprocess
import webbrowser

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(WORKSPACE_DIR, "backend", "autostart.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AUTOSTART] %(message)s",
)
logger = logging.getLogger("TalentOpsAutostart")

def is_port_open(port: int, timeout_sec: float = 1.5) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def is_supervisor_running() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 49151))
        s.close()
        return False
    except OSError:
        return True

def main():
    trigger_type = sys.argv[1] if len(sys.argv) > 1 else "MANUAL_OR_SCHEDULED"
    logger.info(f"Autostart triggered (Source: {trigger_type})")

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    # 1. Ensure Supervisor is running
    if not is_supervisor_running():
        logger.info("Supervisor not running. Launching talentops_supervisor.py...")
        pyw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = "C:\\Python314\\pythonw.exe"
        supervisor_path = os.path.join(WORKSPACE_DIR, "backend", "talentops_supervisor.py")
        subprocess.Popen(
            [pyw, supervisor_path],
            cwd=WORKSPACE_DIR,
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
        )
        time.sleep(2)
    else:
        logger.info("Supervisor is already active.")

    # 2. Check Backend
    if not is_port_open(8000):
        logger.info("Backend port 8000 closed. Waiting for supervisor or launching...")
        time.sleep(3)

    # 3. Check Frontend
    if not is_port_open(5173):
        logger.info("Frontend port 5173 closed. Waiting for supervisor or launching...")
        time.sleep(3)

    backend_ok = is_port_open(8000)
    frontend_ok = is_port_open(5173)

    logger.info(f"Autostart completed. Backend=:8000 ({backend_ok}), Frontend=:5173 ({frontend_ok})")

    # 4. Open browser
    try:
        webbrowser.open("http://localhost:5173")
    except Exception as e:
        logger.debug(f"Browser launch note: {e}")

    # 5. Start-of-Day Antigravity Routine Health & System Check (runs once per day)
    try:
        from daily_antigravity_routine import trigger_daily_antigravity_routine_check
        res = trigger_daily_antigravity_routine_check(source=f"AUTOSTART_{trigger_type}")
        logger.info(f"Daily Antigravity routine check result: {res.get('status')} (CID: {res.get('conversation_id', 'N/A')})")
    except Exception as e:
        logger.error(f"Error triggering daily Antigravity routine check: {e}", exc_info=True)

if __name__ == "__main__":
    main()

