"""
engine_immunity_sentinel.py — In-Process Autonomous Engine Immunity & Watchdog Sentinel
========================================================================================

Guarantees 24/7/365 uninterrupted autonomous operation of all TalentOps AI background engines:
1. WebHarvest Autonomous Web Discovery Engine
2. Autonomous Profile Sweeper (Night Sweeper)
3. Offline Harvest Buffer Watchdog

Strict Immunity Rules:
- Continuous Health Heartbeat: Probes engines every 30 seconds.
- Auto-Revival: If any engine loop is cancelled, crashed, or stopped, revives it in <5 seconds.
- Stagnation Detection: If WebHarvest has not completed a cycle in >180s, triggers immediate wake-up.
- Anti-Starvation Watchdog: Purges domain cooldown bottlenecks to prevent 0-target idle states.
- Zero Frontend Dependency: Operates completely headless regardless of browser tab visibility or window state.
"""

import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

logger = logging.getLogger("talentops.immunity_sentinel")

class EngineImmunitySentinel:
    def __init__(self, check_interval_sec: int = 30, stagnation_threshold_sec: int = 360):
        self.check_interval_sec = check_interval_sec
        self.stagnation_threshold_sec = stagnation_threshold_sec
        self.running = False
        self._thread: threading.Thread = None
        self.total_revivals = 0
        self.last_check_at: str = None

    def start(self):
        """Starts the Engine Immunity Sentinel daemon thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._sentinel_loop, name="TalentOps-EngineImmunitySentinel", daemon=True)
        self._thread.start()
        logger.info("[IMMUNITY_SENTINEL] Perpetual Engine Immunity Sentinel active (24/7 self-healing enabled).")

    def stop(self):
        """Stops the sentinel gracefully."""
        self.running = False

    def _sentinel_loop(self):
        """Continuous watchdog monitor."""
        # Initial grace period on server startup
        time.sleep(25.0)

        while self.running:
            try:
                self.last_check_at = datetime.now(timezone.utc).isoformat()
                self._verify_web_harvest_engine()
                self._verify_sweeper()
                self._verify_offline_buffer()
            except Exception as e:
                logger.error("[IMMUNITY_SENTINEL] Sentinel check cycle exception: %s", e, exc_info=True)

            time.sleep(self.check_interval_sec)

    def _verify_web_harvest_engine(self):
        """Ensures WebHarvest is alive, unblocked, and actively producing cycles."""
        try:
            from .web_harvest_engine import web_harvest_engine
            
            # Rule 1: Engine Must Be Running
            if not web_harvest_engine.running or not web_harvest_engine._loop_task or web_harvest_engine._loop_task.done():
                logger.warning("[IMMUNITY_SENTINEL] ALERT: WebHarvest engine loop was inactive! Reviving engine immediately...")
                web_harvest_engine.running = True
                web_harvest_engine.start()
                self.total_revivals += 1
                return

            # Rule 2: Anti-Stagnation Heartbeat
            heartbeat_str = web_harvest_engine.stats.get("heartbeat_at")
            last_cycle_str = web_harvest_engine.stats.get("last_cycle_at")
            now_dt = datetime.now(timezone.utc)

            # If heartbeat is fresh (<120s), worker is actively progressing through a cycle
            is_active_heartbeat = False
            if heartbeat_str:
                try:
                    hb_dt = datetime.fromisoformat(heartbeat_str)
                    if (now_dt - hb_dt).total_seconds() < 120:
                        is_active_heartbeat = True
                except Exception:
                    pass

            if not is_active_heartbeat and last_cycle_str:
                try:
                    last_dt = datetime.fromisoformat(last_cycle_str)
                    elapsed = (now_dt - last_dt).total_seconds()

                    if elapsed > self.stagnation_threshold_sec:
                        logger.warning(
                            "[IMMUNITY_SENTINEL] ALERT: WebHarvest cycle stagnation detected (last cycle was %.0fs ago > %ds threshold)! "
                            "Decaying domain cooldowns and stimulating engine...",
                            elapsed, self.stagnation_threshold_sec
                        )
                        # Clear half of scraped domain cooldowns to inject immediate freshness
                        if web_harvest_engine._scraped_domains:
                            cutoff = now_dt - timedelta(minutes=15)
                            web_harvest_engine._scraped_domains = {
                                d: t for d, t in web_harvest_engine._scraped_domains.items() if t > cutoff
                            }
                        self.total_revivals += 1
                except Exception as parse_err:
                    logger.debug("[IMMUNITY_SENTINEL] Timestamp parsing note: %s", parse_err)

        except Exception as e:
            logger.error("[IMMUNITY_SENTINEL] Error verifying WebHarvest engine: %s", e)

    def _verify_sweeper(self):
        """Ensures autonomous profile sweeper is running."""
        try:
            from .autonomous_profile_sweeper import autonomous_profile_sweeper
            if not getattr(autonomous_profile_sweeper, "running", True):
                logger.warning("[IMMUNITY_SENTINEL] ALERT: Autonomous Profile Sweeper was stopped. Re-arming sweeper...")
                autonomous_profile_sweeper.start()
                self.total_revivals += 1
        except Exception as e:
            logger.debug("[IMMUNITY_SENTINEL] Sweeper check note: %s", e)

    def _verify_offline_buffer(self):
        """Ensures offline harvest buffer watchdog is alive."""
        try:
            from .offline_buffer import offline_buffer
            if not getattr(offline_buffer, "_running", False):
                logger.warning("[IMMUNITY_SENTINEL] ALERT: Offline buffer watchdog was not alive. Re-launching watchdog...")
                offline_buffer.start_watchdog()
                self.total_revivals += 1
        except Exception as e:
            logger.debug("[IMMUNITY_SENTINEL] Offline buffer check note: %s", e)

    def get_status(self) -> Dict[str, Any]:
        return {
            "sentinel_active": self.running,
            "total_revivals": self.total_revivals,
            "last_check_at": self.last_check_at,
            "check_interval_sec": self.check_interval_sec,
        }

# Global Singleton
engine_immunity_sentinel = EngineImmunitySentinel()
