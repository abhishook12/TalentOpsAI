#!/usr/bin/env python
"""
Autonomous Background Constitutional Quality & Enrichment Sweeper - TalentOps AI

Can be run standalone via CLI or runs automatically inside FastAPI lifespan.
Enforces the 18:00 - 04:00 daily operating window (unless --force is passed).

Usage:
  python autonomous_night_sweeper.py               # Runs continuously in background
  python autonomous_night_sweeper.py --once        # Executes a single sweep pass
  python autonomous_night_sweeper.py --force       # Forces immediate sweeping regardless of current hour
  python autonomous_night_sweeper.py --batch 200   # Custom batch size
"""

import sys
import os
import time
import argparse
import logging

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.autonomous_profile_sweeper import autonomous_sweeper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("autonomous_night_sweeper")


def parse_args():
    parser = argparse.ArgumentParser(description="TalentOps AI Autonomous Background Sweeper")
    parser.add_argument("--once", action="store_true", help="Run a single batch sweep and exit")
    parser.add_argument("--force", action="store_true", help="Force sweep even if outside 18:00-04:00 window")
    parser.add_argument("--batch", type=int, default=100, help="Batch size per sweep (default: 100)")
    parser.add_argument("--delay", type=float, default=1.0, help="Sleep delay between batches in seconds")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.force:
        autonomous_sweeper.force_active = True
    autonomous_sweeper.batch_size = args.batch
    autonomous_sweeper.batch_delay = args.delay

    print("=" * 80)
    print("[TALENTOPS AI] AUTONOMOUS BACKGROUND PROFILE SWEEPER")
    print(f"Schedule: 18:00 to 04:00 Daily (Force Mode: {autonomous_sweeper.force_active})")
    print(f"Batch Size: {args.batch} records | Delay: {args.delay}s | Single-Pass: {args.once}")
    print("=" * 80)

    if args.once:
        print(f"[{time.strftime('%X')}] Running single-pass sweep batch...")
        res = autonomous_sweeper.sweep_batch(limit=args.batch)
        print(f"[{time.strftime('%X')}] Sweep Pass Completed!")
        print(f"Scanned: {res['count']} | Repaired: {res['repaired']} | Duration: {res['duration']}s")
        print("\nTelemetry Stats:")
        for k, v in autonomous_sweeper.stats.items():
            print(f"  - {k}: {v}")
        return

    # Continuous Mode
    autonomous_sweeper.running = True
    pass_count = 1
    
    try:
        while autonomous_sweeper.running:
            if autonomous_sweeper.is_window_active:
                print(f"\n[{time.strftime('%X')}] --- SWEEP CYCLE #{pass_count} ---")
                res = autonomous_sweeper.sweep_batch(limit=args.batch)
                print(
                    f"[{time.strftime('%X')}] Cycle #{pass_count} finished: "
                    f"{res['count']} scanned, {res['repaired']} repaired in {res['duration']}s"
                )
                pass_count += 1
                
                if res["count"] > 0:
                    time.sleep(args.delay)
                else:
                    print(f"[{time.strftime('%X')}] All profiles currently clean! Resting 20 seconds...")
                    time.sleep(20)
            else:
                now_str = time.strftime("%H:%M:%S")
                print(f"[{now_str}] Outside 18:00 - 04:00 window. Sweeper sleeping until evening (6:00 PM)...")
                time.sleep(60)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%X')}] Shutting down Autonomous Sweeper gracefully.")
        print("\nSession Final Stats:")
        for k, v in autonomous_sweeper.stats.items():
            print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
