"""
talentops_supervisor.py — Autonomous OS-Level Process Supervisor & Perpetual Daemon
====================================================================================

Guarantees the TalentOps AI backend server and all autonomous engines run 24/7/365:
- Probes http://127.0.0.1:8000/ping every 15 seconds.
- Automatically restarts uvicorn if it crashes, freezes, or terminates for any reason.
- Detects PC sleep / wake / hibernation jumps and triggers instant health recovery.
- Runs completely headless in the background via pythonw.exe (0 console windows).
- Works 100% independently of browser visibility, tabs, or user session state.
"""

import os
import sys
import time
import socket
import logging
import urllib.request
import subprocess
from datetime import datetime, timezone

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(WORKSPACE_DIR, "backend", "supervisor.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SUPERVISOR] %(message)s",
)
logger = logging.getLogger("TalentOpsSupervisor")

PID_FILE = os.path.join(WORKSPACE_DIR, "backend", "supervisor.pid")
LOCK_PORT = 49151  # Single-instance socket mutex

def acquire_instance_lock():
    """Ensures only a single instance of the supervisor runs across the entire PC."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except Exception:
        logger.info("Another supervisor instance is already running. Exiting redundant process.")
        sys.exit(0)

def is_backend_responsive(timeout_sec: float = 3.0) -> bool:
    """Pings the local backend /ping health endpoint."""
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/ping", headers={"User-Agent": "TalentOpsSupervisor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            return response.status == 200
    except Exception:
        return False

def launch_backend_process() -> subprocess.Popen:
    """Spawns uvicorn server in a detached background process."""
    logger.info("Relaunching TalentOps AI backend server (uvicorn on port 8000)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = WORKSPACE_DIR

    # Windows creation flag for completely detached, zero-window execution
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=WORKSPACE_DIR,
        env=env,
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info(f"Backend launched successfully with PID {proc.pid}")
    return proc

def run_supervisor_loop():
    """Main continuous supervisor loop."""
    lock_sock = acquire_instance_lock()
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    logger.info(f"TalentOps Perpetual Process Supervisor started (PID={os.getpid()}). Workdir: {WORKSPACE_DIR}")

    consecutive_failures = 0
    last_loop_time = time.time()

    while True:
        try:
            current_time = time.time()
            elapsed = current_time - last_loop_time

            # Sleep / Hibernate Wake Detection: If clock jumped forward >60s, PC was sleeping
            if elapsed > 65.0:
                logger.info(f"PC Wake-from-sleep detected (jump of {elapsed:.1f}s). Performing fast recovery probe...")
                consecutive_failures = 0

            last_loop_time = current_time

            if is_backend_responsive(timeout_sec=3.0):
                if consecutive_failures > 0:
                    logger.info("Backend health restored (responding 200 OK).")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(f"Backend probe failed ({consecutive_failures}/3).")

                if consecutive_failures >= 3:
                    logger.error("Backend unresponsive for 3 consecutive probes. Triggering automatic restart...")
                    launch_backend_process()
                    consecutive_failures = 0
                    time.sleep(15.0)  # Grace period for startup

        except Exception as e:
            logger.error(f"Error in supervisor loop: {e}", exc_info=True)

        time.sleep(15.0)

if __name__ == "__main__":
    run_supervisor_loop()
