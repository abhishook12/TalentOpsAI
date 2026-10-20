"""
run.py — One-Command Universal Launcher for TalentOps AI
Starts both Backend (FastAPI :8000) and Frontend (Vite :5173),
verifies health, opens the browser, and handles graceful shutdown on Ctrl+C.
"""
import sys
import os
import time
import subprocess
import webbrowser
import urllib.request
import signal

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))

def is_port_open(port):
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def main():
    print("=" * 70)
    print("   TALENTOPS AI: ONE-COMMAND ALL-IN-ONE LOCAL LAUNCHER")
    print("=" * 70)
    
    # 1. Start or verify Backend
    backend_proc = None
    if is_port_open(8000):
        print("[✓] Backend is already running on http://localhost:8000")
    else:
        print("[..] Starting FastAPI Backend on port 8000...")
        env = os.environ.copy()
        env["PYTHONPATH"] = WORKSPACE_DIR
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=WORKSPACE_DIR,
            env=env
        )

    # 2. Start or verify Frontend
    frontend_proc = None
    if is_port_open(5173):
        print("[✓] Frontend is already running on http://localhost:5173")
    else:
        print("[..] Starting Vite Frontend on port 5173...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=os.path.join(WORKSPACE_DIR, "frontend"),
            shell=True
        )

    # 3. Wait briefly and open browser
    time.sleep(2)
    print("\n[✓] Opening browser at http://localhost:5173 ...")
    webbrowser.open("http://localhost:5173")

    print("\n" + "=" * 70)
    print("TalentOps AI is LIVE!")
    print("  • Web App:      http://localhost:5173")
    print("  • Backend API:  http://localhost:8000")
    print("  • API Docs:     http://localhost:8000/docs")
    print("Press Ctrl+C anytime to stop all services.")
    print("=" * 70 + "\n")

    def handle_exit(sig=None, frame=None):
        print("\nStopping TalentOps AI services...")
        if frontend_proc:
            try: frontend_proc.terminate()
            except Exception: pass
        if backend_proc:
            try: backend_proc.terminate()
            except Exception: pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, handle_exit)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_exit()

if __name__ == "__main__":
    main()
