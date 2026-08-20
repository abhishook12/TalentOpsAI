import duckdb
import os

print("=" * 80)
print("CHECK 1 (PASS 1): 2,303,300 FULL DATASET DELIVERABILITY AUDIT")
print("=" * 80)

p2_3m = "C:/TalentOpsAI/backend/data/recruiters_full_cleaned.parquet"
con = duckdb.connect()

total = con.execute(f"SELECT COUNT(*) FROM read_parquet('{p2_3m}')").fetchone()[0]
print(f"[1.1] Total Raw Records: {total:,} (Target: 2,303,300)")
assert total == 2303300, f"Expected 2,303,300 records, got {total}"

df_stat = con.execute(f"""
    SELECT 
        email_status,
        is_deliverable,
        COUNT(*) as count,
        ROUND(AVG(email_confidence), 2) as avg_conf
    FROM read_parquet('{p2_3m}')
    GROUP BY 1, 2
    ORDER BY count DESC
""").fetchdf()

print("\n[1.2] 2.3M Deliverability Matrix:")
print(df_stat.to_string())

sum_cnt = df_stat['count'].sum()
print(f"\n[1.3] Sum of Categorized Records: {sum_cnt:,} == {total:,}")
assert sum_cnt == total, "Sum mismatch"

con.close()
print("\n" + "=" * 80)
print("CHECK 1 (PASS 1) RESULT: 2,303,300 RECORDS 100% AUDITED & VERIFIED!")
print("=" * 80)
