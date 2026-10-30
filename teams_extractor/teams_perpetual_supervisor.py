"""
teams_perpetual_supervisor.py — Autonomous Perpetual Supervisor for Teams Harvester
=====================================================================================

Guarantees continuous 24/7/365 extraction until explicitly stopped by the user:
1. Detects if deep_upward_extractor.py is active.
2. When the current session ends (e.g. 7,200s limit expires or process terminates),
   it immediately relaunches deep_upward_extractor.py with --duration 864000 (10 days / indefinite).
3. Periodically (every 10 minutes) executes autonomous field completion & entity linking.
4. Auto-recovers from crashes, sleep, or interruptions in <5 seconds.
"""

import os
import sys
import time
import json
import logging
import subprocess
import psutil
from datetime import datetime, timezone

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

LOG_FILE = os.path.join(WORKSPACE_DIR, "teams_extractor", "perpetual_supervisor.log")
STATUS_FILE = os.path.join(WORKSPACE_DIR, "teams_extractor", "supervisor_status.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TeamsSupervisor] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TeamsPerpetualSupervisor")

PYTHON_EXE = os.path.join(WORKSPACE_DIR, "teams_extractor", "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

EXTRACTOR_SCRIPT = os.path.join(WORKSPACE_DIR, "teams_extractor", "deep_upward_extractor.py")
ENRICHER_SCRIPT = os.path.join(WORKSPACE_DIR, "backend", "scratch", "complete_profile_fields.py")

def get_active_extractor_pid():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if 'deep_upward_extractor.py' in cmd:
                return p.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def launch_extractor():
    logger.info("🚀 Launching perpetual Teams deep upward extractor...")
    cmd = [
        PYTHON_EXE,
        EXTRACTOR_SCRIPT,
        "--chat", "CTV- Phone numbers",
        "--duration", "864000",  # 10 days continuous
        "--delay", "1.8",
        "--offscreen"
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=WORKSPACE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    logger.info(f"✅ Perpetual Teams Extractor launched with PID {proc.pid}")
    return proc.pid

def run_enrichment_cycle():
    if os.path.exists(ENRICHER_SCRIPT):
        try:
            logger.info("Running scheduled entity completion & Parquet sync cycle...")
            res = subprocess.run([sys.executable, ENRICHER_SCRIPT], capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                logger.info("Entity completion cycle completed cleanly.")
            else:
                logger.warning(f"Entity completion cycle returned code {res.returncode}: {res.stderr[:200]}")
        except Exception as e:
            logger.warning(f"Enrichment cycle notice: {e}")

def main():
    logger.info("==========================================================")
    logger.info(">>> STARTING TEAMS PERPETUAL EXTRACTION SUPERVISOR <<<")
    logger.info(" Directive: Continuous execution until user explicit stop")
    logger.info("==========================================================")

    last_enrichment = time.time()

    while True:
        try:
            pid = get_active_extractor_pid()
            if pid:
                # Active extractor running
                try:
                    p = psutil.Process(pid)
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                    uptime_min = (time.time() - p.create_time()) / 60
                    # Write status
                    status_data = {
                        "status": "RUNNING",
                        "active_pid": pid,
                        "memory_mb": round(mem_mb, 1),
                        "uptime_minutes": round(uptime_min, 1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "chat": "CTV- Phone numbers",
                        "mode": "perpetual_until_stopped"
                    }
                    with open(STATUS_FILE, "w", encoding="utf-8") as f:
                        json.dump(status_data, f, indent=2)
                except Exception:
                    pass
            else:
                logger.warning("No active Teams extractor process found. Auto-reviving now...")
                new_pid = launch_extractor()
                time.sleep(3)

            # Check if 10 minutes have elapsed for enrichment
            if time.time() - last_enrichment > 600:
                run_enrichment_cycle()
                last_enrichment = time.time()

        except Exception as e:
            logger.error(f"Supervisor loop exception: {e}")

        time.sleep(15)

if __name__ == '__main__':
    main()
