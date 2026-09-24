#!/usr/bin/env python
"""
Autonomous Background Constitutional Quality & Enrichment Sweeper - TalentOps AI
(Mirrored in backend/scripts/autonomous_night_sweeper.py)
"""
import sys
import os

# Delegate directly to the root autonomous_night_sweeper
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from autonomous_night_sweeper import main

if __name__ == "__main__":
    main()
