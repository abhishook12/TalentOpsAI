# admin_utils.py – Helper for managing background worker subprocesses

import subprocess
import sys
import os
import time
from pathlib import Path
from threading import Lock
import threading
from collections import deque
from typing import Dict, Any, List

# Mapping of worker name to script filename (relative to project root)
_WORKER_SCRIPTS = {
    "discovery_worker": "background_workers/discovery_worker.py",
    "bulk_enhancer": "background_workers/bulk_enhancer.py",
    "taxonomy_worker": "background_workers/taxonomy_worker.py",
}

# In‑memory registry of running processes
_workers: Dict[str, Dict[str, Any]] = {}
_registry_lock = Lock()

def _script_path(name: str) -> Path:
    """Return absolute path to the script for *name*.
    Raises KeyError if the name is unknown.
    """
    rel = _WORKER_SCRIPTS[name]
    return Path(__file__).resolve().parents[3] / rel

def _read_stream(stream, logs_deque):
    for line in iter(stream.readline, b''):
        try:
            text = line.decode('utf-8').rstrip()
            logs_deque.append(text)
        except Exception:
            pass

def start_worker(name: str) -> Dict[str, Any]:
    """Start the worker *name* if not already running.
    Returns a dict with ``pid`` and ``status``.
    """
    if name not in _WORKER_SCRIPTS:
        raise ValueError(f"Unknown worker: {name}")
    with _registry_lock:
        info = _workers.get(name)
        if info and info["process"].poll() is None:
            # already running
            return {"pid": info["process"].pid, "status": "running"}
        script = _script_path(name)
        
        args = [sys.executable, "-u", str(script)]
        if name == "discovery_worker":
            args.extend(["--scan-interval-hours", "0.02"]) # Every 1.2 minutes
            
        # Use the same Python interpreter that runs this process
        proc = subprocess.Popen(args,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 cwd=Path.cwd())
        
        logs_deque = deque(maxlen=200)
        _workers[name] = {
            "process": proc,
            "start_time": time.time(),
            "last_run": None,
            "logs": logs_deque
        }
        
        threading.Thread(target=_read_stream, args=(proc.stdout, logs_deque), daemon=True).start()
        threading.Thread(target=_read_stream, args=(proc.stderr, logs_deque), daemon=True).start()
        
        return {"pid": proc.pid, "status": "started"}

def stop_worker(name: str) -> Dict[str, Any]:
    """Stop a running worker if present.
    Returns a dict with ``status``.
    """
    with _registry_lock:
        info = _workers.get(name)
        if not info:
            return {"status": "not_found"}
        proc = info["process"]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            return {"status": "stopped", "pid": proc.pid}
        else:
            return {"status": "already_exited"}

def get_status() -> List[Dict[str, Any]]:
    """Return a list of status dictionaries for each known worker.
    Fields: name, pid (or null), status (running/stopped/unknown),
    uptime_seconds (or null).
    """
    now = time.time()
    result = []
    with _registry_lock:
        for name in _WORKER_SCRIPTS:
            info = _workers.get(name)
            if info:
                proc = info["process"]
                if proc.poll() is None:
                    status = "running"
                    pid = proc.pid
                    uptime = now - info["start_time"]
                else:
                    status = "stopped"
                    pid = None
                    uptime = None
            else:
                status = "stopped"
                pid = None
                uptime = None
            result.append({
                "name": name,
                "pid": pid,
                "status": status,
                "uptime_seconds": uptime,
            })
    return result

def get_logs(name: str) -> List[str]:
    """Return the latest logs for the worker *name*."""
    with _registry_lock:
        info = _workers.get(name)
        if info and "logs" in info:
            return list(info["logs"])
        return []
