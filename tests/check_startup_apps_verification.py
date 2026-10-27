"""
check_startup_apps_verification.py — Verification Check 2
Tests idempotent execution and process integrity of ensure_daily_work_apps().
"""
import sys
import psutil

sys.path.insert(0, r"c:\TalentOpsAI")
from autostart_talentops import ensure_daily_work_apps, is_process_running

print("--- CHECK 2: IDEMPOTENT EXECUTION & PROCESS INTEGRITY CHECK ---")

# Count processes before
vitel_count_before = len([p for p in psutil.process_iter(["name"]) if p.info["name"] and "vitel" in p.info["name"].lower()])
outlook_count_before = len([p for p in psutil.process_iter(["name"]) if p.info["name"] and "outlook" in p.info["name"].lower()])

print(f"Active Vitel processes before: {vitel_count_before}")
print(f"Active Outlook processes before: {outlook_count_before}")
print(f"is_process_running('Vitelglobal.exe'): {is_process_running('Vitelglobal.exe')}")
print(f"is_process_running('OUTLOOK.EXE'): {is_process_running('OUTLOOK.EXE')}")

assert is_process_running("Vitelglobal.exe") is True, "Vitel process not detected!"
assert is_process_running("OUTLOOK.EXE") is True, "Outlook process not detected!"

# Run ensure_daily_work_apps
print("Invoking ensure_daily_work_apps()...")
ensure_daily_work_apps()

# Count processes after
vitel_count_after = len([p for p in psutil.process_iter(["name"]) if p.info["name"] and "vitel" in p.info["name"].lower()])
outlook_count_after = len([p for p in psutil.process_iter(["name"]) if p.info["name"] and "outlook" in p.info["name"].lower()])

print(f"Active Vitel processes after: {vitel_count_after}")
print(f"Active Outlook processes after: {outlook_count_after}")

assert vitel_count_before == vitel_count_after, f"Duplicate Vitel process spawned! Before={vitel_count_before}, After={vitel_count_after}"
assert outlook_count_before == outlook_count_after, f"Duplicate Outlook process spawned! Before={outlook_count_before}, After={outlook_count_after}"

print("Idempotency verified: Exactly 0 duplicate processes created.")
print(">>> CHECK 2 PASSED WITH COMPLETE PROOF <<<")
