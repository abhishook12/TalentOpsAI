"""
chrome_tab_refresher.py — Root CLI entrypoint for Daily Chrome Tab Refresher
"""

import sys
import os
import json

WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.app.services.chrome_tab_refresher import chrome_tab_refresher

if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    status_only = "--status" in sys.argv or "-s" in sys.argv

    if status_only:
        state = chrome_tab_refresher.read_state()
        print(json.dumps(state, indent=2))
        sys.exit(0)

    delay = 0.5
    for arg in sys.argv:
        if arg.startswith("--delay="):
            try:
                delay = float(arg.split("=")[1])
            except ValueError:
                pass

    res = chrome_tab_refresher.refresh_all_tabs(force=force, source="CLI_COMMAND", tab_delay_sec=delay)
    print(json.dumps(res, indent=2))
