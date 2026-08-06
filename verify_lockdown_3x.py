import sys
import os
import time

sys.path.append(r"C:\TalentOpsAI\backend")
from app.resource_lockdown import is_locked_down, _get_lockdown_state
from app.services.resource_lockdown import ResourceLockdownController

def verify():
    print("Starting 3-Pass Verification for Emergency Lockdown Status...\n")
    for i in range(1, 4):
        print(f"--- PASS {i} ---")
        
        locked = is_locked_down()
        state = _get_lockdown_state()
        service_state = ResourceLockdownController.get_status()
        
        if locked or state.get("is_locked") or service_state.get("is_locked_down"):
            print(f"FAIL: System is still locked down! Reason: {state.get('reason')} / {service_state.get('lockdown_reason')}")
            sys.exit(1)
            
        print("SUCCESS: System is operating normally, no lockdown active.")
        time.sleep(1) # wait between checks
        
    print("\nFINAL RESULT: 3/3 Passes completed successfully. Emergency Lockdown is lifted.")

if __name__ == "__main__":
    verify()
