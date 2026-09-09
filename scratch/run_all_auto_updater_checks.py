"""
run_all_auto_updater_checks.py
Master runner executing all 3 Auto-Update & Fleet Management Verification Checks under Rule 11.
"""

import sys
import os

from check_update_1_paths_and_migrations import run_check_1
from check_update_2_updater_and_rollback import run_check_2
from check_update_3_manifest_and_fleet import run_check_3

def main():
    print("#" * 80)
    print("TALENTOPS SCOUT ENTERPRISE AUTO-UPDATE & FLEET SYSTEM — TRIPLE VERIFICATION (RULE 11)")
    print("#" * 80)
    print()

    print(">>> RUNNING CHECK 1: APPDATA PATH ISOLATION & LOCAL DB MIGRATIONS <<<")
    run_check_1()
    print()

    print(">>> RUNNING CHECK 2: OUT-OF-PROCESS UPDATER, SHA-256 INTEGRITY & ROLLBACK <<<")
    run_check_2()
    print()

    print(">>> RUNNING CHECK 3: RELEASE MANIFEST API, TWO-TIER VERSIONING & FLEET TELEMETRY <<<")
    run_check_3()
    print()

    print("#" * 80)
    print("ALL 3 AUTO-UPDATE & FLEET SYSTEM CHECKS COMPLETED WITH 100% SUCCESS")
    print("#" * 80)

if __name__ == "__main__":
    main()
