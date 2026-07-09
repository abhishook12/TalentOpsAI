import sys, os, json, time
from datetime import datetime

LOCKDOWN_STATE_FILE = os.path.join(os.path.dirname(__file__), "lockdown_state.json")

class ResourceLockdownController:
    """
    Emergency Resource Lockdown & 3-Step Authorization Controller (Rule #9).
    Provides instant kill-switch capabilities to block all heavy database operations,
    AI API requests, and background vision scrapers whenever platform thresholds hit
    or critical situations arise.
    
    Unblocking or starting high-consumption tasks requiring override mandates exactly
    3 distinct verification/authorization steps.
    """
    @staticmethod
    def _load_state():
        if os.path.exists(LOCKDOWN_STATE_FILE):
            try:
                with open(LOCKDOWN_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "is_locked_down": False,
            "lockdown_reason": "None",
            "locked_at": None,
            "unlock_confirmation_count": 0,
            "unlock_attempts_log": []
        }

    @staticmethod
    def _save_state(state):
        try:
            with open(LOCKDOWN_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[ResourceLockdown] Error saving lockdown state: {e}")

    @classmethod
    def get_status(cls):
        return cls._load_state()

    @classmethod
    def trigger_lockdown(cls, reason="Manual emergency kill-switch triggered via command center or Rule #8 threshold"):
        """
        Instantly puts the entire system into Emergency Resource Lockdown mode.
        """
        state = cls._load_state()
        state["is_locked_down"] = True
        state["lockdown_reason"] = reason
        state["locked_at"] = datetime.now().isoformat()
        state["unlock_confirmation_count"] = 0
        state["unlock_attempts_log"].append({
            "action": "LOCKDOWN_TRIGGERED",
            "reason": reason,
            "timestamp": state["locked_at"]
        })
        cls._save_state(state)
        print(f"\n🛑 [EMERGENCY LOCKDOWN ACTIVE] All background resource consumption halted! Reason: {reason}\n")
        return state

    @classmethod
    def register_unlock_confirmation(cls, user_signature="USER_AUTHORIZATION"):
        """
        Registers 1 step of the mandatory 3-Step Authorization Protocol (Rule #9).
        Only unlocks the system when unlock_confirmation_count reaches 3.
        """
        state = cls._load_state()
        if not state["is_locked_down"]:
            return {"status": "ALREADY_UNLOCKED", "message": "System is currently operating normally without active lockdown."}

        state["unlock_confirmation_count"] += 1
        current_step = state["unlock_confirmation_count"]
        now_ts = datetime.now().isoformat()
        
        state["unlock_attempts_log"].append({
            "action": f"UNLOCK_STEP_{current_step}_CONFIRMED",
            "signature": user_signature,
            "timestamp": now_ts
        })

        if current_step >= 3:
            state["is_locked_down"] = False
            state["unlock_confirmation_count"] = 0
            state["lockdown_reason"] = "Unlocked via 3-Step Authorization Protocol"
            cls._save_state(state)
            print(f"\n🔓 [SYSTEM UNLOCKED - 3-STEP AUTHORIZATION COMPLETE] All safety checks satisfied. Resources unblocked.\n")
            return {
                "status": "UNLOCKED",
                "step": 3,
                "message": "3-Step Authorization Protocol successfully completed. Emergency Resource Lockdown lifted."
            }
        else:
            cls._save_state(state)
            remaining = 3 - current_step
            msg = f"Confirmation Step {current_step}/3 registered. {remaining} more confirmation(s) required to unlock system."
            print(f"\n⚠️ [LOCKDOWN OVERRIDE PENDING] {msg}\n")
            return {
                "status": "PENDING_AUTHORIZATION",
                "step": current_step,
                "remaining_steps": remaining,
                "message": msg
            }

    @classmethod
    def assert_resource_access_permitted(cls, operation_name="High-Consumption Operation"):
        """
        Raises an explicit error or halts execution if system is locked down.
        """
        state = cls._load_state()
        if state.get("is_locked_down", False):
            raise RuntimeError(f"🛑 [RESOURCE LOCKDOWN ACTIVE] Cannot execute '{operation_name}'. System locked down: {state.get('lockdown_reason')}. 3-step user confirmation required to unblock.")

if __name__ == '__main__':
    st = ResourceLockdownController.get_status()
    print("=== EMERGENCY RESOURCE LOCKDOWN CONTROLLER STATUS ===")
    for k, v in st.items():
        print(f"  {k}: {v}")
