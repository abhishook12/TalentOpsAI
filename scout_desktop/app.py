"""
app.py — Master Desktop Companion Application for TalentOps Scout

Orchestrates:
- Native Win32 Active Window & Process Tracking (<1ms)
- Background Autonomous Visual Sampling & 64x64 Regional Diffing
- Offline Native Windows Media OCR & Deep Entity Intelligence
- Evidence Grounding Gate & Observation Knowledge Graph
- Offline Local SQLite Staging Queue Buffer
- Live Backend Synchronization (/recruiters/extension/batch)
- Auto-Purge Temporary Screenshot Buffer Lifecycle (15-30s TTL, 0ms on noise)
- Windows System Tray & Executive Floating Companion UI
"""

import os
import sys
import time
import uuid
import logging
from typing import Optional, Dict, Any, List

from PIL import Image

from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtCore import QObject, Signal, QTimer, Slot
from PySide6.QtGui import QIcon

from .core.window_tracker import WindowTracker, WindowInfo
from .core.browser_tracker import BrowserTracker
from .core.visual_sampler import VisualSampler
from .core.evidence_store import EvidenceStore
from .core.ocr_engine import OcrEngine
from .core.intelligence_levels import IntelligenceRouter, FrameQueue, FrameContext
from .core.context_memory import ContextMemory
from .extractor.entity_extractor import EntityExtractor
from .extractor.grounding_gate import GroundingGate
from .extractor.identity_resolver import IdentityResolver
from .extractor.timeline_parser import TimelineParser
from .sync.local_queue import LocalQueue
from .sync.backend_client import BackendClient
from .sync.batch_processor import BatchProcessor
from .ui.tray import SystemTrayManager
from .ui.main_window import MainWindow
from .ui.edge_handle import EdgeHandleWidget
from .ui.diagnostics_window import DiagnosticsWindow
from .ui.settings_window import SettingsWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scout.app")


class AppBridge(QObject):
    """Thread-safe signal bridge for Qt UI updates."""
    window_updated = Signal(object, dict)         # (WindowInfo, browser_dict)
    state_updated = Signal(str)                   # "ACTIVE_SAMPLING" | "IDLE_WATCH" | "PAUSED"
    frame_processed = Signal(str, float, object, object, str, object) # (capture_id, delta, img, win_info, url, entities)
    metrics_updated = Signal(dict)
    event_logged = Signal(str, str)               # (event_name, details)
    capture_view_updated = Signal(str, float, str, object, dict, str) # (capture_id, delta, reason, img, breakdown, status)
    extraction_proof_updated = Signal(list)       # (observations)
    db_proof_updated = Signal(str, dict, str)     # (status, response_dict, result_str)


class ScoutDesktopApp:
    def __init__(self):
        self.bridge = AppBridge()

        # Core Subsystems
        self.window_tracker = WindowTracker()
        self.browser_tracker = BrowserTracker()
        self.evidence_store = EvidenceStore()
        self.ocr_engine = OcrEngine()
        self.entity_extractor = EntityExtractor()
        self.local_queue = LocalQueue()
        self.backend_client = BackendClient()

        # New Intelligence Subsystems (Phases 3-9)
        self.intelligence_router = IntelligenceRouter()
        self.context_memory = ContextMemory()
        self.grounding_gate = GroundingGate()
        self.identity_resolver = IdentityResolver()
        self.timeline_parser = TimelineParser()
        self.batch_processor = BatchProcessor()
        self.frame_queue = FrameQueue(max_depth=5)

        # State tracking
        self.current_window: Optional[WindowInfo] = None
        self.current_browser_context: Dict[str, Any] = {}

        # 12 Explicit Telemetry Counters
        self.cnt_captured = 0
        self.cnt_analyzed = 0
        self.cnt_useful = 0
        self.cnt_staged = 0
        self.cnt_matched = 0
        self.cnt_new = 0
        self.cnt_enriched = 0
        self.cnt_db_updates = 0
        self.cnt_purged = 0
        self.cnt_observed = 0       # Total observations extracted
        self.cnt_fields_added = 0   # Total new field values added

        # Autonomous Visual Engine
        self.sampler = VisualSampler(
            on_meaningful_frame=self._on_meaningful_frame,
            on_state_change=self._on_sampler_state_change,
        )

        # UI Components (3-Level Architecture)
        # Level 1: SystemTrayManager
        # Level 2: EdgeHandleWidget (persistent screen-edge dock handle)
        # Level 3: MainWindow (full companion window with min/max/close)
        self.main_window = MainWindow()
        self.edge_handle = EdgeHandleWidget()
        self.tray = SystemTrayManager()
        self.diagnostics = DiagnosticsWindow()
        self.settings_window = SettingsWindow(self.backend_client, self.local_queue)

        self._connect_signals()
        self._init_timers()

    def _connect_signals(self):
        # Bridge to Level 3 Main Window
        self.bridge.window_updated.connect(self._handle_window_ui_update)
        self.bridge.state_updated.connect(self._handle_state_ui_update)
        self.bridge.metrics_updated.connect(self.main_window.update_explicit_counters)
        self.bridge.event_logged.connect(self.main_window.log_event)
        self.bridge.capture_view_updated.connect(self.main_window.update_latest_capture)
        self.bridge.extraction_proof_updated.connect(self.main_window.update_extraction_proof)
        self.bridge.db_proof_updated.connect(self.main_window.update_database_proof)
        self.bridge.frame_processed.connect(self.diagnostics.update_diagnostics)

        # Level 2 Edge Handle action -> Toggle Main Window
        self.edge_handle.clicked.connect(self._toggle_main_window)

        # Level 1 Tray actions
        self.tray.show_overlay.connect(self._show_main_window)
        self.tray.show_diagnostics.connect(self.diagnostics.show)
        self.tray.show_settings.connect(self.settings_window.show)
        self.tray.show_connection_status.connect(self._show_connection_status)
        self.tray.force_capture.connect(self.force_capture)
        self.tray.toggle_pause.connect(self.toggle_pause)
        self.tray.quit_app.connect(self.shutdown)

        # Level 3 Main Window actions
        self.main_window.force_capture_requested.connect(self.force_capture)
        self.main_window.open_diagnostics_requested.connect(self.diagnostics.show)
        self.main_window.open_settings_requested.connect(self.settings_window.show)
        self.main_window.shutdown_requested.connect(self.shutdown)
        self.main_window.dock_to_edge_requested.connect(self._dock_to_edge)

        # Settings actions
        self.settings_window.force_sync_requested.connect(self._flush_queue_to_backend)

    def _dock_to_edge(self):
        """Hides MainWindow while ensuring the screen-edge handle is active and visible."""
        self.main_window.hide()
        if not self.edge_handle.isVisible():
            self.edge_handle.show()

    def _toggle_main_window(self):
        """Toggles visibility of the Level 3 Main Window."""
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
        else:
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()

    def _show_main_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _show_connection_status(self):
        self.settings_window.show()
        tab = self.settings_window.findChild(QTabWidget)
        if tab:
            tab.setCurrentIndex(2)

    def _init_timers(self):
        # 1. Window Monitor Timer (polls active window every 400ms)
        self.window_timer = QTimer()
        self.window_timer.timeout.connect(self._poll_active_window)
        self.window_timer.start(400)

        # 2. Auto-Purge Timer (cleans expired screenshots every 15 seconds)
        self.purge_timer = QTimer()
        self.purge_timer.timeout.connect(self._run_purge_sweep)
        self.purge_timer.start(15000)

        # 3. Queue Sync Timer (flushes pending batches to backend every 10 seconds)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._flush_queue_to_backend)
        self.sync_timer.start(10000)

        # 4. Heartbeat Timer (pings /scout/heartbeat every 20 seconds)
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.heartbeat_timer.start(20000)

    def start(self):
        """
        Starts the autonomous desktop scout with visible startup progression:
        STARTING -> CONNECTING -> BACKEND CONNECTED -> WINDOW DETECTED -> SCOUT ACTIVE
        """
        logger.info("🚀 TalentOps Scout Desktop starting...")
        self.tray.show()
        self.edge_handle.show()
        self.main_window.show()

        # Update environment badge
        self.main_window.update_environment(
            self.backend_client.environment_name,
            self.backend_client.active_api_base
        )

        # Step 1: STARTING
        self.main_window.update_status_state("STARTING")
        self.bridge.event_logged.emit("SYSTEM_STARTING", "Initializing autonomous subsystems...")
        QApplication.processEvents()

        # Step 2: CONNECTING
        self.main_window.update_status_state("CONNECTING")
        self.bridge.event_logged.emit("BACKEND_CONNECTING", f"Connecting to {self.backend_client.environment_name}...")
        QApplication.processEvents()

        # Step 3: BACKEND CONNECTED / OFFLINE
        ok, res = self.backend_client.send_heartbeat(status="STARTING")
        if ok:
            self.main_window.update_status_state("BACKEND CONNECTED")
            self.main_window.ind_backend.set_state("CONNECTED")
            self.bridge.event_logged.emit("BACKEND_CONNECTED", f"Ready ({self.backend_client.environment_name})")
        else:
            self.main_window.update_status_state("CONNECTING")
            self.main_window.ind_backend.set_state("OFFLINE")
            self.bridge.event_logged.emit("BACKEND_OFFLINE", f"Offline mode active: {res.get('error', '')}")
        QApplication.processEvents()

        # Step 4: WINDOW DETECTED
        win = self.window_tracker.get_active_window()
        if win.is_valid:
            self.current_window = win
            self.main_window.update_status_state("WINDOW DETECTED")
            self.main_window.ind_window.set_state("DETECTED")
            b_ctx = {}
            if win.is_browser:
                b_ctx = self.browser_tracker.resolve_browser_context(win.hwnd, win.title)
                self.current_browser_context = b_ctx
            self.bridge.window_updated.emit(win, b_ctx)
            self.bridge.event_logged.emit("WINDOW_DETECTED", f"[{win.process_name}] {win.title[:30]}")
            QApplication.processEvents()

        # Step 5: SCOUT ACTIVE
        self.sampler.start(initial_window=self.current_window)
        self.main_window.update_status_state("ACTIVE")
        self.edge_handle.set_status_state("ACTIVE")
        self.tray.update_icon_status("ACTIVE")
        self.bridge.event_logged.emit("SCOUT_ACTIVE", "Autonomous visual watch loop running")

        # Initial immediate capture if valid window is already active
        if self.current_window and self.current_window.is_valid:
            self.sampler.trigger_immediate_capture(self.current_window, reason="startup_initial")

        self._emit_telemetry()

    def _poll_active_window(self):
        """Checks foreground window and triggers immediate capture on change."""
        try:
            win = self.window_tracker.get_active_window()
            if not win.is_valid:
                return

            if self.window_tracker.has_active_window_changed(win):
                self.current_window = win
                self.sampler.set_current_window(win)
                b_ctx = {}
                if win.is_browser:
                    b_ctx = self.browser_tracker.resolve_browser_context(win.hwnd, win.title)
                    self.current_browser_context = b_ctx

                logger.info("Active window switched: [%s] '%s'", win.process_name, win.title[:40])
                self.bridge.window_updated.emit(win, b_ctx)
                self.bridge.event_logged.emit("WINDOW_DETECTED", f"[{win.process_name}] {win.title[:35]}")

                if win.is_browser and b_ctx.get("platform"):
                    self.bridge.event_logged.emit("PAGE_CONTEXT_DETECTED", f"Platform: {b_ctx.get('platform')}")

                # Immediate capture on window change (Zero wait!)
                self.sampler.trigger_immediate_capture(win, reason="window_changed")
        except Exception as e:
            logger.debug("Active window poll error: %s", e)

    def _on_meaningful_frame(self, img: Image.Image, delta: float, win_info: WindowInfo):
        """
        Invoked by VisualSampler when meaningful visual change occurs.
        """
        self.cnt_captured += 1
        capture_id = f"VC-{uuid.uuid4().hex[:6].upper()}"
        b_ctx = self.current_browser_context
        page_url = b_ctx.get("url", "")
        page_title = b_ctx.get("title", win_info.title)
        cand_name = b_ctx.get("candidate_name")

        self.bridge.event_logged.emit("SCREENSHOT_CAPTURED", f"ID: {capture_id} (Delta: {delta*100:.1f}%)")

        # 1. Save frame in temporary evidence store
        capture_item = self.evidence_store.save_capture(
            img=img,
            capture_id=capture_id,
            page_url=page_url,
            window_title=page_title,
            change_score=delta,
        )
        self.evidence_store.update_status(capture_id, "ANALYZING")
        self.cnt_analyzed += 1
        self.bridge.event_logged.emit("ANALYSIS_STARTED", f"Scanning frame {capture_id} on {win_info.process_name}")

        # 2. Extract visible text via offline Windows Media OCR
        ocr_lines = []
        if capture_item and os.path.exists(capture_item.file_path):
            ocr_lines = self.ocr_engine.extract_text_from_image(capture_item.file_path)

        lines = list(ocr_lines)

        clusters = self.entity_extractor.extract_from_lines(
            lines=lines,
            capture_id=capture_id,
            source_url=page_url,
            window_title=page_title,
            inferred_candidate=cand_name,
        )

        # 3. Stage & transition capture lifecycle
        breakdown = {"people": 0, "companies": 0, "locations": 0, "jobs": 0, "signals": 0}
        proof_items = []

        if clusters:
            self.cnt_useful += 1
            self.evidence_store.update_status(capture_id, "EXTRACTED", clusters)

            for c in clusters:
                # Track observations through grounding gate
                for obs in c.observations:
                    self.cnt_observed += 1

                    # Validate through grounding gate
                    grounding_result = self.grounding_gate.validate_observation(
                        obs_dict=obs.to_dict(),
                        capture_context={"capture_id": capture_id, "page_url": page_url}
                    )

                    # Track field additions via context memory
                    entity_state = self.context_memory.find_entity_by_name(
                        c.canonical_name, c.entity_type
                    )
                    if entity_state is None:
                        entity_state = self.context_memory.register_entity(
                            entity_id=f"ENT-{uuid.uuid4().hex[:8].upper()}",
                            entity_type=c.entity_type,
                            canonical_name=c.canonical_name,
                            source_url=page_url,
                            capture_id=capture_id,
                        )

                    is_new_field = self.context_memory.update_entity_field(
                        entity_id=entity_state.entity_id,
                        field_name=obs.predicate,
                        value=obs.object_value,
                        predicate=obs.predicate,
                    )
                    if is_new_field:
                        self.cnt_fields_added += 1

                    proof_items.append({
                        "field": obs.predicate.replace("HAS_", "").replace("WORKS_", ""),
                        "value": str(obs.object_value),
                        "confidence": obs.confidence,
                        "evidence": obs.evidence or f"Visual capture {capture_id}",
                        "decision": grounding_result.outcome if hasattr(grounding_result, 'outcome') else (
                            "ACCEPT" if obs.confidence >= 0.90 else "ENRICH"
                        ),
                    })

                staged_contact = c.to_staged_contact_dict()
                staged_contact["capture_id"] = capture_id
                staged_contact["source_url"] = page_url
                staged_contact["source_page_title"] = page_title
                staged_contact["visual_change_score"] = delta
                if not staged_contact.get("linkedin_url") and page_url and "linkedin.com/in/" in page_url:
                    staged_contact["linkedin_url"] = page_url
                self.local_queue.enqueue_cluster(staged_contact)
                self.cnt_staged += 1

                if c.entity_type == "JOB":
                    breakdown["jobs"] += 1
                else:
                    breakdown["people"] += 1
                if c.current_company:
                    breakdown["companies"] += 1
                if c.location:
                    breakdown["locations"] += 1
                breakdown["signals"] += len(c.observations)

            self.evidence_store.update_status(capture_id, "STAGED")
            self.bridge.event_logged.emit("ENTITY_FOUND", f"{len(clusters)} candidate(s) — {clusters[0].canonical_name}")
            self.bridge.event_logged.emit("STAGING_CREATED", f"Enqueued to SQLite buffer ({len(clusters)} items)")

            first = clusters[0]
            desc = f"👤 {first.canonical_name}"
            if first.current_title:
                desc += f" — {first.current_title}"
            if first.current_company:
                desc += f" @ {first.current_company}"
            if first.location:
                desc += f" ({first.location})"
            self.main_window.lbl_target_desc.setText(f"Extracted: {desc}")
        else:
            # Discard immediately on NO_USEFUL_DATA (0ms)
            self.evidence_store.update_status(capture_id, "NO_USEFUL_DATA")
            self.cnt_purged += 1
            self.bridge.event_logged.emit("SCREENSHOT_PURGED", f"{capture_id} discarded (0ms, no useful data)")

        # 4. Update UI proof views
        self.bridge.capture_view_updated.emit(
            capture_id, delta, "VISUAL_DELTA", img, breakdown,
            "STAGED" if clusters else "PURGED"
        )
        self.bridge.extraction_proof_updated.emit(proof_items)
        self.bridge.frame_processed.emit(capture_id, delta, img, win_info, page_url, clusters)
        self._emit_telemetry()

    def _on_sampler_state_change(self, state: str):
        self.bridge.state_updated.emit(state)

    def _run_purge_sweep(self):
        purged = self.evidence_store.purge_expired()
        if purged > 0:
            self.cnt_purged += purged
            self.bridge.event_logged.emit("SCREENSHOT_PURGED", f"Auto-purged {purged} expired screenshot(s)")
        self._emit_telemetry()

    def _flush_queue_to_backend(self):
        """Flushes pending local SQLite queue items to backend /recruiters/extension/batch."""
        pending = self.local_queue.get_pending_batch(limit=20)
        if not pending:
            return

        queue_ids = [item.pop("_local_queue_id") for item in pending]
        for it in pending:
            it.pop("_retry_count", None)

        self.bridge.event_logged.emit(
            "DB_SYNC_STARTED",
            f"Flushing {len(pending)} records to {self.backend_client.environment_name}"
        )

        success, res = self.backend_client.sync_staged_batch(
            contacts=pending,
            session_stats={"source": "TalentOps Scout Desktop"},
        )

        if success:
            self.local_queue.mark_batch_synced(queue_ids)
            staged_cnt = res.get("staged", len(pending))
            self.cnt_db_updates += staged_cnt

            proc = res.get("processor_stats", {})
            self.cnt_new += proc.get("new", 0)
            self.cnt_enriched += proc.get("enriched", 0)
            self.cnt_matched += proc.get("duplicate", 0) + proc.get("review", 0)

            self.bridge.event_logged.emit("DB_SYNC_SUCCESS", f"Backend accepted {staged_cnt} staged record(s)")
            self.bridge.db_proof_updated.emit("STAGED", res, f"SUCCESS (Staged: {staged_cnt})")
        else:
            err = res.get("error", "Network error")
            self.local_queue.mark_batch_failed(queue_ids, err)
            self.bridge.event_logged.emit("DB_SYNC_FAILED", f"Error: {err}")
            self.bridge.db_proof_updated.emit("ERROR", res, f"FAILED: {err}")

        self._emit_telemetry()

    def _send_heartbeat(self):
        b_ctx = self.current_browser_context
        self.backend_client.send_heartbeat(
            page_url=b_ctx.get("url"),
            client_metrics={
                "state": self.sampler.state,
                "captured": self.cnt_captured,
                "analyzed": self.cnt_analyzed,
                "useful": self.cnt_useful,
                "staged": self.cnt_staged,
                "observed": self.cnt_observed,
                "fields_added": self.cnt_fields_added,
                "purged": self.cnt_purged,
                "committed": self.cnt_db_updates,
                "intelligence_level": self.intelligence_router.stats.get("total_decisions", 0),
                "context_entities": len(self.context_memory.get_all_entities()),
                "frame_queue_depth": self.frame_queue.depth,
            }
        )

    def _emit_telemetry(self):
        e_stats = self.evidence_store.get_telemetry()
        metrics = {
            "captured": self.cnt_captured,
            "analyzed": self.cnt_analyzed,
            "useful": self.cnt_useful,
            "staged": self.cnt_staged,
            "matched": self.cnt_matched,
            "new": self.cnt_new,
            "enriched": self.cnt_enriched,
            "db_updates": self.cnt_db_updates,
            "purged": self.cnt_purged,
            "observed": self.cnt_observed,
            "fields_added": self.cnt_fields_added,
            "buffer_current": e_stats["active_buffer_images"],
            "buffer_max": 20,
        }
        self.bridge.metrics_updated.emit(metrics)

    @Slot(object, dict)
    def _handle_window_ui_update(self, win: WindowInfo, b_ctx: dict):
        app_name = win.process_name
        title = b_ctx.get("title", win.title)
        url = b_ctx.get("url", "")
        cand = b_ctx.get("candidate_name")
        context_str = f"Candidate: {cand}" if cand else (b_ctx.get("platform") or "Active Screen")
        self.main_window.update_window_context(app_name, title, url, context_str)

    @Slot(str)
    def _handle_state_ui_update(self, state: str):
        self.main_window.update_status_state(state)
        self.edge_handle.set_status_state(state)
        self.tray.update_icon_status(state)
        pulse_text = "⚡ SAMPLING (1.0s interval)" if "ACTIVE" in state else "💤 IDLE WATCH (10s static rule)"
        self.main_window.lbl_sampling_pulse.setText(pulse_text)

    def force_capture(self):
        """Developer force capture trigger."""
        if self.current_window:
            logger.info("⚡ Force Capture initiated.")
            self.sampler.trigger_immediate_capture(self.current_window, reason="developer_force")

    def toggle_pause(self):
        if self.sampler.state == "PAUSED":
            self.sampler.resume()
        else:
            self.sampler.pause()

    def shutdown(self):
        logger.info("🛑 Complete shutdown initiated: stopping all TalentOps Scout operations...")
        try:
            self.sampler.stop()
        except Exception as e:
            logger.debug("Error stopping sampler: %s", e)

        for t_attr in ("window_timer", "purge_timer", "sync_timer", "heartbeat_timer"):
            try:
                timer = getattr(self, t_attr, None)
                if timer and timer.isActive():
                    timer.stop()
            except Exception as e:
                logger.debug("Error stopping timer %s: %s", t_attr, e)

        self.main_window._is_shutting_down = True
        for w_attr in ("edge_handle", "main_window", "diagnostics", "settings_window"):
            try:
                win = getattr(self, w_attr, None)
                if win:
                    win.close()
            except Exception as e:
                logger.debug("Error closing %s: %s", w_attr, e)

        try:
            if hasattr(self, "tray") and hasattr(self.tray, "tray"):
                self.tray.tray.hide()
        except Exception as e:
            logger.debug("Error hiding tray: %s", e)

        try:
            if hasattr(self, "local_queue"):
                self.local_queue.close()
        except Exception as e:
            logger.debug("Error closing local queue: %s", e)

        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "assets", "logo.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "logo.png"),
        r"c:\TalentOpsAI\talentops-logo.png",
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            app.setWindowIcon(QIcon(p))
            break

    scout = ScoutDesktopApp()
    scout.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
