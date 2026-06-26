import psycopg

conn = psycopg.connect(
    'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
)
cur = conn.cursor()

# Check breakdown of existing repair_reason tags
cur.execute("""
    SELECT repair_reason, count(*) 
    FROM recruiters 
    WHERE repair_reason IS NOT NULL AND repair_reason != ''
    GROUP BY repair_reason
    ORDER BY count(*) DESC
""")
print("=== EXISTING repair_reason BREAKDOWN ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check if any have metadata_json with pre_repair_corrupted
cur.execute("""
    SELECT count(*) FROM recruiters 
    WHERE metadata_json LIKE '%pre_repair_corrupted%'
""")
print(f"\nRecords with pre_repair_corrupted metadata: {cur.fetchone()[0]}")

# Check 5 examples of repaired_column_swap to verify they look correct
cur.execute("""
    SELECT recruiter_id, recruiter_name, company_id, email, repair_reason
    FROM recruiters
    WHERE repair_reason = 'repaired_column_swap'
    LIMIT 5
""")
print("\n=== SAMPLE repaired_column_swap records ===")
for row in cur.fetchall():
    print(f"  ID={row[0]}, Name={row[1]}, CompanyID={row[2]}, Email={row[3]}")

# Check how many of the 18774 target pool still need tagging
cur.execute("""
    SELECT count(*) FROM recruiters r
    JOIN companies c ON r.company_id = c.company_id
    WHERE r.repair_reason IS NULL OR r.repair_reason = ''
""")
print(f"\nRecruiters with NO repair_reason (joined to companies): {cur.fetchone()[0]}")

conn.close()
