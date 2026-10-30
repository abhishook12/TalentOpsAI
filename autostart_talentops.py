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

def is_process_running(proc_name) -> bool:
    """Checks if a process is active by executable image name."""
    target_names = [p.lower() for p in proc_name] if isinstance(proc_name, (list, tuple)) else [proc_name.lower()]
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if any(name == t or name == f"{t}.exe" or (t.endswith(".exe") and name == t) for t in target_names):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.warning(f"psutil check failed for {proc_name}: {e}")
        try:
            for t in target_names:
                res = subprocess.run(
                    ["tasklist", "/fi", f"IMAGENAME eq {t}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if t in res.stdout.lower():
                    return True
        except Exception:
            pass
    return False

def resolve_teams_exe() -> str:
    """Resolves the installed Microsoft Teams executable path."""
    import glob
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe"),
        r"C:\Program Files\WindowsApps\ms-teams.exe",
    ]
    winapps = glob.glob(r"C:\Program Files\WindowsApps\MSTeams_*\ms-teams.exe")
    if winapps:
        candidates.insert(0, winapps[0])
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def ensure_application_running(app_name: str, exe_path: str, proc_name) -> bool:
    """
    Ensures that a desktop application (such as Vitel Global, Outlook, or Teams) is running.
    If not already running, launches it safely via Windows Shell / detached process.
    If already running, logs status and does not spawn duplicate instances.
    """
    if is_process_running(proc_name):
        logger.info(f"{app_name} ({proc_name}) is already running. No launch needed.")
        return True

    if not os.path.exists(exe_path):
        logger.error(f"{app_name} executable not found at {exe_path}")
        return False

    logger.info(f"Launching {app_name} from {exe_path}...")
    try:
        if hasattr(os, "startfile"):
            os.startfile(exe_path)
        else:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            with open(os.devnull, "wb") as devnull:
                subprocess.Popen(
                    [exe_path],
                    creationflags=creation_flags,
                    stdin=devnull,
                    stdout=devnull,
                    stderr=devnull,
                    close_fds=True,
                )
        logger.info(f"{app_name} launched successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to launch {app_name}: {e}")
        return False

def ensure_daily_work_apps():
    """
    Ensures daily essential work applications are running:
    1. Vitel Global (Softphone / Dialing / SMS)
    2. Microsoft Outlook (Email / Calendar)
    3. Microsoft Teams (Chat / Collaboration / Calls)
    """
    apps = [
        {
            "name": "Vitel Global",
            "exe": r"C:\Users\User\AppData\Local\com.vitelglobal.vitelgloabalapp.winx\Vitelglobal.exe",
            "proc": "Vitelglobal.exe",
        },
        {
            "name": "Microsoft Outlook",
            "exe": r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
            "proc": "OUTLOOK.EXE",
        },
        {
            "name": "Microsoft Teams",
            "exe": resolve_teams_exe(),
            "proc": ["ms-teams.exe", "ms-teams", "teams.exe", "teams"],
        },
    ]

    for app in apps:
        ensure_application_running(app["name"], app["exe"], app["proc"])

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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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

    # 6. Ensure Daily Work Applications (Vitel Global, Outlook & Microsoft Teams) are active
    try:
        ensure_daily_work_apps()
    except Exception as e:
        logger.error(f"Error ensuring daily work applications: {e}", exc_info=True)

if __name__ == "__main__":
    main()

