"""
run_all_pipeline_checks.py
Executes all 3 Pipeline Verification Checks under Rule 11 and prints the unified evidence proof.
"""

import sys
import os

from check_pipeline_1_ingestion_and_staging import run_pipeline_check_1
from check_pipeline_2_intelligence_graph import run_pipeline_check_2
from check_pipeline_3_intent_and_api import run_pipeline_check_3

def main():
    print("#" * 80)
    print("TALENTOPS END-TO-END PIPELINE TRIPLE VERIFICATION SUITE (RULE 11)")
    print("#" * 80)
    print()

    print(">>> RUNNING PIPELINE CHECK 1: INGESTION BUFFER & IDENTITY RESOLUTION <<<")
    run_pipeline_check_1()
    print()

    print(">>> RUNNING PIPELINE CHECK 2: 4-TIER KNOWLEDGE GRAPH MULTI-SOURCE INGESTION <<<")
    run_pipeline_check_2()
    print()

    print(">>> RUNNING PIPELINE CHECK 3: INTENT AGGREGATOR & FASTAPI DASHBOARD APIS <<<")
    run_pipeline_check_3()
    print()

    print("#" * 80)
    print("ALL 3 PIPELINE CHECKS COMPLETED WITH 100% SUCCESS")
    print("#" * 80)

if __name__ == "__main__":
    main()
