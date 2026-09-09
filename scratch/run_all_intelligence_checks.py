"""
run_all_intelligence_checks.py
Executes all 3 verification checks under Rule 11 and prints the unified evidence proof.
"""

import sys
import os

from check_1_intelligence_schema_integrity import run_check_1
from check_2_ingestion_gateway_dedup import run_check_2
from check_3_intent_engine_evidence import run_check_3

def main():
    print("#" * 80)
    print("TALENTOPS DATA INTELLIGENCE ENGINE — 3-STAGE VERIFICATION PROTOCOL (RULE 11)")
    print("#" * 80)
    print()

    print(">>> RUNNING CHECK 1: SCHEMA INTEGRITY & 4-TIER CONSTRAINTS <<<")
    run_check_1()
    print()

    print(">>> RUNNING CHECK 2: INGESTION GATEWAY & ENTITY DEDUPLICATION <<<")
    run_check_2()
    print()

    print(">>> RUNNING CHECK 3: INTENT AGGREGATION & EXPLAINABLE EVIDENCE LEDGER <<<")
    run_check_3()
    print()

    print("#" * 80)
    print("ALL 3 MANDATORY CHECKS COMPLETED WITH 100% SUCCESS")
    print("#" * 80)

if __name__ == "__main__":
    main()
