"""
talentops_supervisor.py — Autonomous OS-Level Process Supervisor & Perpetual Daemon
====================================================================================

Guarantees the TalentOps AI local environment runs 24/7/365:
- Probes http://127.0.0.1:8000/ping every 15 seconds (Backend).
- Probes http://127.0.0.1:5173 every 15 seconds (Vite Frontend).
- Automatically restarts uvicorn or Vite if either crashes, freezes, or terminates.
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

def is_frontend_responsive(timeout_sec: float = 2.0) -> bool:
    """Checks if Vite frontend is listening on port 5173."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            return s.connect_ex(("127.0.0.1", 5173)) == 0
    except Exception:
        return False

def launch_backend_process() -> subprocess.Popen:
    """Spawns uvicorn server in a detached, 100% hidden background process."""
    logger.info("Relaunching TalentOps AI backend server (uvicorn on port 8000)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = WORKSPACE_DIR

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    py_exe = sys.executable
    if sys.platform == "win32" and "python.exe" in py_exe.lower():
        pyw = py_exe.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pyw):
            py_exe = pyw

    cmd = [
        py_exe,
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]

    uvicorn_log_path = os.path.join(WORKSPACE_DIR, "backend", "uvicorn_live.log")
    log_fp = open(uvicorn_log_path, "a", encoding="utf-8")

    proc = subprocess.Popen(
        cmd,
        cwd=WORKSPACE_DIR,
        env=env,
        creationflags=creation_flags,
        stdin=subprocess.DEVNULL,
        stdout=log_fp,
        stderr=log_fp,
        shell=False,
    )
    logger.info(f"Backend launched successfully with PID {proc.pid}")
    return proc

def launch_frontend_process() -> subprocess.Popen:
    """Spawns Vite frontend server in a detached, 100% hidden background process without cmd.exe."""
    logger.info("Relaunching TalentOps AI frontend server (Vite on port 5173)...")
    env = os.environ.copy()

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    frontend_dir = os.path.join(WORKSPACE_DIR, "frontend")
    vite_js = os.path.join(frontend_dir, "node_modules", "vite", "bin", "vite.js")

    node_exe = None
    common_node_paths = [
        "C:\\Program Files\\nodejs\\node.exe",
        "C:\\Program Files (x86)\\nodejs\\node.exe",
        os.path.expandvars("%APPDATA%\\npm\\node.exe"),
        os.path.expandvars("%LOCALAPPDATA%\\Programs\\node\\node.exe"),
    ]
    for p in common_node_paths:
        if os.path.exists(p):
            node_exe = p
            break

    if not node_exe:
        import shutil
        node_exe = shutil.which("node") or "node"

    frontend_log_path = os.path.join(WORKSPACE_DIR, "backend", "frontend_live.log")
    log_fp = open(frontend_log_path, "a", encoding="utf-8")

    cmd = [node_exe, vite_js] if os.path.exists(vite_js) else [node_exe, os.path.join(frontend_dir, "node_modules", ".bin", "vite")]

    proc = subprocess.Popen(
        cmd,
        cwd=frontend_dir,
        env=env,
        creationflags=creation_flags,
        stdin=subprocess.DEVNULL,
        stdout=log_fp,
        stderr=log_fp,
        shell=False,
    )
    logger.info(f"Frontend launched successfully (100% headless) with PID {proc.pid}")
    return proc

def run_supervisor_loop():
    """Main continuous supervisor loop monitoring both Backend and Frontend."""
    lock_sock = acquire_instance_lock()
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    logger.info(f"TalentOps Perpetual Process Supervisor started (PID={os.getpid()}). Workdir: {WORKSPACE_DIR}")

    backend_fails = 0
    frontend_fails = 0
    last_loop_time = time.time()

    # Initial check & launch
    if not is_backend_responsive(timeout_sec=2.0):
        logger.info("Initial check: Backend not responding. Launching...")
        launch_backend_process()
    if not is_frontend_responsive(timeout_sec=2.0):
        logger.info("Initial check: Frontend not responding. Launching...")
        launch_frontend_process()

    while True:
        try:
            current_time = time.time()
            elapsed = current_time - last_loop_time

            # Sleep / Hibernate Wake Detection: If clock jumped forward >60s, PC was sleeping
            if elapsed > 65.0:
                logger.info(f"PC Wake-from-sleep detected (jump of {elapsed:.1f}s). Performing fast recovery probe...")
                backend_fails = 0
                frontend_fails = 0
                # Start-of-day Antigravity check trigger (asynchronously checks if new day has started)
                try:
                    import threading
                    def _wake_routine_worker():
                        time.sleep(3.0)  # Allow backend/frontend probe recovery first
                        try:
                            if WORKSPACE_DIR not in sys.path:
                                sys.path.insert(0, WORKSPACE_DIR)
                            from daily_antigravity_routine import trigger_daily_antigravity_routine_check
                            trigger_daily_antigravity_routine_check(source="PC_WAKE_SLEEP_DETECTION")
                        except Exception as err:
                            logger.error(f"Error in wake-from-sleep Antigravity routine worker: {err}")

                    threading.Thread(target=_wake_routine_worker, daemon=True, name="WakeAntigravityCheck").start()
                except Exception as ex:
                    logger.error(f"Failed to spawn wake Antigravity check thread: {ex}")

            last_loop_time = current_time


            # 1. Probe Backend (Port 8000)
            if is_backend_responsive(timeout_sec=3.0):
                if backend_fails > 0:
                    logger.info("Backend health restored (responding 200 OK).")
                backend_fails = 0
            else:
                backend_fails += 1
                logger.warning(f"Backend probe failed ({backend_fails}/5).")
                if backend_fails >= 5:
                    logger.error("Backend unresponsive for 5 consecutive probes. Triggering automatic restart...")
                    launch_backend_process()
                    backend_fails = 0
                    time.sleep(20.0)

            # 2. Probe Frontend (Port 5173)
            if is_frontend_responsive(timeout_sec=2.0):
                if frontend_fails > 0:
                    logger.info("Frontend health restored (responding on port 5173).")
                frontend_fails = 0
            else:
                frontend_fails += 1
                logger.warning(f"Frontend probe failed ({frontend_fails}/5).")
                if frontend_fails >= 5:
                    logger.error("Frontend unresponsive for 5 consecutive probes. Triggering automatic restart...")
                    launch_frontend_process()
                    frontend_fails = 0
                    time.sleep(10.0)

        except Exception as e:
            logger.error(f"Error in supervisor loop: {e}", exc_info=True)

        time.sleep(15.0)

if __name__ == "__main__":
    run_supervisor_loop()
