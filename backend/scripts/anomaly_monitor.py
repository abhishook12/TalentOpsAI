import time
import subprocess
import os
import sys

def main():
    print("Starting Anomaly Monitor Daemon...")
    while True:
        print("\n--- Running automated database anomaly cleanup ---")
        try:
            # Run the general anomaly fix script
            subprocess.run([sys.executable, "scripts/fix_all_anomalies.py"], check=True)
            
            # Run the domain mismatch fix script
            subprocess.run([sys.executable, "scripts/fix_mismatched_domains.py"], check=True)
            
            print("Cleanup completed successfully.")
        except Exception as e:
            print(f"Error during automated cleanup: {e}")
            
        print("Sleeping for 12 hours...")
        time.sleep(12 * 3600)  # Wait 12 hours

if __name__ == "__main__":
    main()
