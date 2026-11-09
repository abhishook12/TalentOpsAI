"""
SAFE REPLACE PARQUET
====================
Safely updates recruiters_full.parquet without Windows file lock collisions.
"""
import sys, os, time, subprocess
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import duckdb

WORKSPACE_DIR = r"C:\TalentOpsAI"
PARQUET_PATH = os.path.join(WORKSPACE_DIR, "backend", "data", "recruiters_full.parquet")
TEMP_PARQUET_PATH = os.path.join(WORKSPACE_DIR, "backend", "data", "recruiters_full_clean.parquet")

print("1. Loading and purging ghost shadows in DuckDB...", flush=True)
con = duckdb.connect()
con.execute(f"CREATE TABLE master AS SELECT * FROM read_parquet('{PARQUET_PATH}')")
initial_cnt = con.execute("SELECT count(*) FROM master").fetchone()[0]
print(f"   Initial Parquet count: {initial_cnt}", flush=True)

con.execute("""
    WITH teams_recs AS (
        SELECT lower(trim(recruiter_name)) AS tname
        FROM master
        WHERE data_source = 'teams' AND phone IS NOT NULL AND phone != ''
        GROUP BY 1
    )
    DELETE FROM master
    WHERE data_source != 'teams' 
      AND (phone IS NULL OR phone = '')
      AND lower(trim(recruiter_name)) IN (SELECT tname FROM teams_recs);
""")

post_cnt = con.execute("SELECT count(*) FROM master").fetchone()[0]
deleted = initial_cnt - post_cnt
print(f"   Purged {deleted} empty ghost records.", flush=True)
print(f"   Clean Parquet count: {post_cnt}", flush=True)

con.execute(f"COPY master TO '{TEMP_PARQUET_PATH}' (FORMAT PARQUET)")
con.close()

print("2. Stopping uvicorn to release Windows read lock...", flush=True)
# Find and stop uvicorn
cmd_stop = "Get-CimInstance Win32_Process -Filter \"name = 'pythonw.exe'\" | Where-Object { $_.CommandLine -like '*uvicorn*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
subprocess.run(["powershell", "-Command", cmd_stop], capture_output=True)
time.sleep(1.0)

print("3. Replacing live Parquet file...", flush=True)
os.replace(TEMP_PARQUET_PATH, PARQUET_PATH)
print("   Parquet replaced successfully!", flush=True)

print("4. Restarting uvicorn background server...", flush=True)
env = os.environ.copy()
env["PYTHONPATH"] = WORKSPACE_DIR
log_fp = open(os.path.join(WORKSPACE_DIR, "backend", "uvicorn_live.log"), "a", encoding="utf-8")
proc = subprocess.Popen(
    [r"C:\Python314\pythonw.exe", "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=WORKSPACE_DIR,
    env=env,
    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    stdin=subprocess.DEVNULL,
    stdout=log_fp,
    stderr=log_fp,
    shell=False
)
print(f"   Uvicorn restarted with PID {proc.pid}", flush=True)

# Wait for ping
time.sleep(2.0)
print("\n=== SAFE PARQUET REPLACEMENT COMPLETE! ===", flush=True)
