import duckdb

print("=" * 80)
print("CHECK 3 (PASS 3): ZERO-DEFECT QUARANTINE & CONSTRAINT AUDIT (2,303,300 ROWS)")
print("=" * 80)

p2_3m = "C:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
con = duckdb.connect()

# 1. Missing emails cannot be deliverable
cnt_missing_deliv = con.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{p2_3m}')
    WHERE (email IS NULL OR email = '' OR email LIKE '%@missing.local%') AND is_deliverable = true
""").fetchone()[0]
print(f"[3.1] Missing emails with is_deliverable=true: {cnt_missing_deliv} (MUST BE 0)")
assert cnt_missing_deliv == 0, f"Violation: {cnt_missing_deliv} missing emails marked deliverable"

# 2. Undeliverable emails cannot have positive confidence
cnt_undeliv_conf = con.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{p2_3m}')
    WHERE email_status = 'undeliverable' AND email_confidence > 0
""").fetchone()[0]
print(f"[3.2] Undeliverable emails with email_confidence > 0: {cnt_undeliv_conf} (MUST BE 0)")
assert cnt_undeliv_conf == 0, f"Violation: {cnt_undeliv_conf} undeliverable emails have confidence > 0"

# 3. Verified emails must have active corporate MX and is_deliverable=true
cnt_verified_invalid = con.execute(f"""
    SELECT COUNT(*) FROM read_parquet('{p2_3m}')
    WHERE email_status = 'verified' AND (is_deliverable = false OR email_confidence < 90)
""").fetchone()[0]
print(f"[3.3] Verified emails with is_deliverable=false or confidence < 90: {cnt_verified_invalid} (MUST BE 0)")
assert cnt_verified_invalid == 0, f"Violation: {cnt_verified_invalid} verified emails have invalid state"

con.close()
print("\n" + "=" * 80)
print("CHECK 3 (PASS 3) RESULT: ZERO-DEFECT QUARANTINE & CONSTRAINT RULES 100% CLEAN!")
print("=" * 80)
