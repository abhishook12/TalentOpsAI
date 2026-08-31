from app.database import SessionLocal
from app.models.auth_models import User
from app.routes.accounts import list_accounts
from app.routes.health import check_outlook_bridge
from app.services.send_engine import _check_account_health

print("=== CHECK 2: BACKEND ROUTE & SERVICE VERIFICATION ===")
db = SessionLocal()
u = db.query(User).filter(User.id == 56).first()
assert u is not None, "User 56 not found"

# 1. Test Bridge Health check for user 56
bridge_status = check_outlook_bridge(db=db, current_user_id=u.id)
print(f"Bridge Health for user 56: {bridge_status}")
assert bridge_status.get("status") == "ok", f"Bridge health failed: {bridge_status}"

# 2. Test Account List for user 56
accounts_res = list_accounts(db=db, current_user=u)
print(f"Accounts returned for user 56: {len(accounts_res.get('items', []))} item(s)")
assert len(accounts_res.get("items", [])) > 0, "No accounts returned for user 56"
first_acc = accounts_res["items"][0]
print(f"   Default sender: {first_acc.get('display_name')} <{first_acc.get('email_address')}> (provider: {first_acc.get('provider')}, is_default: {first_acc.get('is_default')}, is_shadow_alias: {first_acc.get('is_shadow_alias')})")
assert first_acc.get("is_shadow_alias") is False, "Default account should not be a shadow alias"
assert first_acc.get("email_address") == "abhishekjadon824@gmail.com", "Default account email mismatch"

# 3. Test send engine account health verification
healthy, err = _check_account_health(first_acc.get("account_id"), u.id)
print(f"Send Engine Account Health check: healthy={healthy}, err={err}")
assert healthy is True, f"Account health failed: {err}"

print("CHECK 2 PASSED: All backend routes, health checks, and send engine routines verified successfully.\n")
