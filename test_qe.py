import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.services.quality_engine import QualityEngine

def run_checks():
    print("Testing QualityEngine...", flush=True)
    qe = QualityEngine()
    print("Running Vulnerability Scan...", flush=True)
    qe.run_vulnerability_scan()
    print("Running Process Safe Repairs...", flush=True)
    qe.process_safe_repairs()
    print("Checks complete.", flush=True)

if __name__ == "__main__":
    run_checks()
