import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.resource_lockdown import _get_lockdown_state, _set_lockdown_state, is_locked_down

def main():
    print("=======================================================================")
    print("=== EMERGENCY RESOURCE SHIELD UNLOCK PROTOCOL ===")
    print("=======================================================================")
    
    if not is_locked_down():
        print("[INFO] The system is NOT currently in an Emergency Lockdown state.")
        print("[INFO] No action required.")
        return
        
    state = _get_lockdown_state()
    print(f"\n[ALERT] SYSTEM IS LOCKED DOWN!")
    print(f"[REASON] {state.get('reason')}")
    print(f"[TIMESTAMP] {state.get('timestamp')}")
    
    print("\nTo resume, restart, or unblock the system, you must pass the 3-step verification protocol.")
    print("You must explicitly type 'START' or 'UNBLOCK' exactly 3 separate times.")
    
    successful_attempts = 0
    target_count = 3
    valid_phrases = ["START", "UNBLOCK"]
    
    while successful_attempts < target_count:
        attempt = input(f"[{successful_attempts + 1}/{target_count}] Enter 'START' or 'UNBLOCK' to proceed: ").strip().upper()
        if attempt in valid_phrases:
            successful_attempts += 1
            print(f" -> Accepted ({successful_attempts}/{target_count})")
        else:
            print(" -> Invalid input. You must type 'START' or 'UNBLOCK'. Attempt failed.")
            
    print("\n[SUCCESS] 3-step verification complete.")
    _set_lockdown_state(False)
    print("=======================================================================")
    print("=== SYSTEM UNLOCKED AND READY ===")
    print("=======================================================================")

if __name__ == '__main__':
    main()
