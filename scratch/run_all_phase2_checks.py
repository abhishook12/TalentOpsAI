"""
run_all_phase2_checks.py — Master Triple Verification Runner (User Rule 11 Compliance).

Executes:
- Check 1: Cryptographic Trust Chain, Ed25519 Signatures & Typed State Machine
- Check 2: Staged Rollouts, 3% Circuit Breaker & Node Health Model
- Check 3: E2E Auto-Update, Rollback & AppData Data Loss Prevention Proof
"""

import sys
import os
import subprocess

PYTHON_EXE = r"C:\TalentOpsAI\teams_extractor\venv\Scripts\python.exe"

CHECKS = [
    (
        "Check 1: Cryptographic Trust Chain & Typed State Machine",
        r"c:\TalentOpsAI\scratch\check_update_p2_1_crypto_and_state_machine.py",
    ),
    (
        "Check 2: Staged Rollouts, 3% Circuit Breaker & Node Health Model",
        r"c:\TalentOpsAI\scratch\check_update_p2_2_rollout_and_circuit_breaker.py",
    ),
    (
        "Check 3: E2E Auto-Update, Rollback & AppData Preservation",
        r"c:\TalentOpsAI\scratch\check_update_p2_3_e2e_updater_and_appdata.py",
    ),
]


def main():
    print("#" * 80)
    print("TALENTOPS SCOUT PRODUCTION HARDENING — MASTER TRIPLE CHECK (RULE 11)")
    print("#" * 80)

    results = []
    for title, script_path in CHECKS:
        print(f"\n>>> RUNNING {title.upper()} <<<")
        proc = subprocess.run([PYTHON_EXE, script_path], text=True)
        if proc.returncode == 0:
            results.append((title, "PASSED [OK]"))
        else:
            results.append((title, f"FAILED [CODE {proc.returncode}]"))
            print(f"[FAIL] Execution aborted on {title}")
            sys.exit(proc.returncode)

    print("\n" + "=" * 80)
    print("FINAL TRIPLE VERIFICATION SUMMARY (USER RULE 11 COMPLIANCE)")
    print("=" * 80)
    for title, status in results:
        print(f"  {status} — {title}")

    all_passed = all("PASSED" in s for _, s in results)
    print(f"\nALL 3 CHECKS PASSED: {all_passed}")
    print("=" * 80)

    if not all_passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
