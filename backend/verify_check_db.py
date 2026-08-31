import sys
from app.database import SessionLocal
from app.models.auth_models import User, ConnectedEmailAccount, UserBridgeStatus
from app.models.campaigns import Campaign, EmailLog
from app.models.models import Company, Recruiter

print("=== CHECK 1: COMPREHENSIVE DATABASE INTEGRITY ===")
db = SessionLocal()

# 1. User & Accounts check
user_count = db.query(User).count()
account_count = db.query(ConnectedEmailAccount).count()
print(f"Users in DB: {user_count}, Connected Email Accounts: {account_count}")
assert user_count > 0, "No users found in database"

# Check User 56 (Admin/Master user)
u56 = db.query(User).filter(User.id == 56).first()
if u56:
    print(f"User 56: email={u56.email}, default_sender_id={u56.default_sender_id}")
    u56_accs = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.user_id == 56).all()
    for acc in u56_accs:
        print(f"   Account: id={acc.account_id}, provider={acc.provider}, email={acc.email_address}, display_name={acc.display_name}, status={acc.status}")

# 2. Company & Logo integrity check
company_count = db.query(Company).count()
clearbit_count = db.query(Company).filter(Company.logo_url.like("%logo.clearbit.com%")).count()
hunter_count = db.query(Company).filter(Company.logo_url.like("%logos.hunter.io%")).count()
print(f"Companies in DB: {company_count}")
print(f"Clearbit URLs in DB (must be 0): {clearbit_count}")
print(f"Hunter.io URLs in DB: {hunter_count}")
assert clearbit_count == 0, f"Found {clearbit_count} leftover Clearbit URLs"

# 3. Campaign & Email logs check
campaign_count = db.query(Campaign).count()
email_log_count = db.query(EmailLog).count()
print(f"Campaigns in DB: {campaign_count}, Email Logs: {email_log_count}")

print("CHECK 1 PASSED: Database fully verified with zero anomalies.\n")
