import sys
import os
sys.path.append(r"C:\TalentOpsAI\backend")

from app.services.quality_engine import QualityEngine
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    qe = QualityEngine()
    print("--- Check 1 ---")
    qe.run_vulnerability_scan()
    qe.process_safe_repairs()
    print("Check 1 Passed")
    
    print("--- Check 2 ---")
    qe.run_vulnerability_scan()
    qe.process_safe_repairs()
    print("Check 2 Passed")
    
    print("--- Check 3 ---")
    qe.run_vulnerability_scan()
    qe.process_safe_repairs()
    print("Check 3 Passed")
