"""
Standalone Background Enrichment Runner
========================================
Runs the Zero-Cost Autonomous Enrichment Engine in standalone or daemon mode.
Can be invoked directly: python scripts/background_enricher.py
"""
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("background_enricher")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enrichment_service import enrichment_engine
from app.utils.enricher_state import get_enricher_state

def main():
    print("=================================================================")
    print("=== TALENTOPSAI ZERO-COST AUTONOMOUS ENRICHMENT ENGINE ===")
    print("=================================================================")
    print("Starting background worker daemon on unified Parquet/DuckDB dataset...")
    
    result = enrichment_engine.start()
    print(f"Status: {result.get('message')}")
    
    try:
        while True:
            state = get_enricher_state()
            status = state.get("status", "stopped")
            processed = state.get("records_processed", 0)
            success = state.get("success_count", 0)
            phase = state.get("current_phase", "idle")
            rate = state.get("rate_per_sec", 0)
            
            print(f"[{status.upper()}] Processed: {processed:,} | Enriched: {success:,} | Rate: {rate}/s | Phase: {phase}")
            
            if status == "stopped":
                print("Daemon state marked as stopped. Exiting.")
                break
                
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping enrichment daemon gracefully...")
        enrichment_engine.stop()
        print("Enrichment daemon stopped.")

if __name__ == "__main__":
    main()
