import argparse
import json
import time
import sqlite3
import os

def collect_evidence(log_file):
    evidence = {
        "timestamp": time.time(),
        "log_tail": [],
        "db_stats": {}
    }
    
    # Read last 50 lines of log file
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                evidence["log_tail"] = [line.strip() for line in lines[-50:]]
        except Exception as e:
            evidence["log_tail"] = [f"Error reading log: {e}"]
    else:
        evidence["log_tail"] = ["Log file not found or not provided."]

    # 2. Query Database
    evidence["db_state"] = {}
    try:
        conn = sqlite3.connect(r'C:\TalentOpsAI\backend\dev.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*) FROM recruiters")
        total_recruiters = cursor.fetchone()[0]
        evidence["db_stats"]["total_recruiters"] = total_recruiters
        
        cursor.execute("SELECT count(DISTINCT state) FROM recruiters")
        states_covered = cursor.fetchone()[0]
        evidence["db_stats"]["states_covered"] = states_covered
        
        conn.close()
    except Exception as e:
        evidence["db_stats"]["error"] = str(e)
        
    # Save to JSON
    filename = f"evidence_{int(time.time())}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(evidence, f, indent=2)
        print(f"Evidence collected and saved to {filename}")
    except Exception as e:
        print(f"Failed to save evidence: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect execution evidence")
    parser.add_argument("--log-file", type=str, help="Path to backend log file", default="backend.log")
    args = parser.parse_args()
    
    collect_evidence(args.log_file)
