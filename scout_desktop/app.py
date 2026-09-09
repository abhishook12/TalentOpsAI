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
import json
import uuid
import logging
import tempfile
import threading
from typing import Optional, Dict, Any, List, Tuple

from PIL import Image

from PySide6.QtWidgets import QApplication, QTabWidget, QSystemTrayIcon
from PySide6.QtCore import QObject, Signal, QTimer, Slot
from PySide6.QtGui import QIcon

from .core.window_tracker import WindowTracker, WindowInfo, is_allowed_scout_target
from .core.browser_tracker import BrowserTracker
from .core.visual_sampler import VisualSampler
from .core.evidence_store import EvidenceStore
from .core.ocr_engine import OcrEngine
from .core.updater import AutoUpdater, CURRENT_VERSION
from .core.intelligence_levels import IntelligenceRouter, FrameQueue, FrameContext
from .core.context_memory import ContextMemory
from .extractor.entity_extractor import EntityExtractor
from .extractor.patterns import is_valid_person_name, is_valid_company_name
from .extractor.grounding_gate import GroundingGate
from .extractor.identity_resolver import IdentityResolver
from .extractor.cross_channel_stitcher import CrossChannelStitcher
from .extractor.timeline_parser import TimelineParser
from .sync.local_queue import LocalQueue
from .sync.backend_client import BackendClient
from .sync.batch_processor import BatchProcessor
from .ui.tray import SystemTrayManager
from .ui.main_window import MainWindow
from .ui.edge_handle import EdgeHandleWidget
from .ui.diagnostics_window import DiagnosticsWindow
from .ui.settings_window import SettingsWindow
from .ui.activation_window import ActivationWindow

class NullWriter:
    def write(self, text): pass
    def flush(self): pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scout.app")


class AppBridge(QObject):
    """Thread-safe signal bridge for Qt UI updates."""
    window_updated = Signal(object, dict, bool, str)         # (WindowInfo, browser_dict, is_allowed, target_type)
    state_updated = Signal(str)                   # "ACTIVE_SAMPLING" | "IDLE_WATCH" | "PAUSED"
    frame_processed = Signal(str, float, object, object, str, object) # (capture_id, delta, img, win_info, url, entities)
    metrics_updated = Signal(dict)
    event_logged = Signal(str, str)               # (event_name, details)
    capture_view_updated = Signal(str, float, str, object, dict, str) # (capture_id, delta, reason, img, breakdown, status)
    extraction_proof_updated = Signal(list)       # (observations)
    db_proof_updated = Signal(str, dict, str)     # (status, response_dict, result_str)
    candidate_card_updated = Signal(str, str, str, str, str, str, object) # (name, title, company, location, status, desc, copilot_info)


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

        # Auto-Updater Subsystem (Centralized Single Instance)
        self._pending_update_version = None
        self._pending_installer_path = None
        self._is_update_required = False
        self.updater = AutoUpdater(
            api_base=self.backend_client.active_api_base,
            current_version=CURRENT_VERSION,
            device_id=self.backend_client.device_id,
            on_update_ready=self._on_update_ready,
            on_mandatory_update_required=self._on_mandatory_update_required,
        )
        self.updater.start()

        # New Intelligence Subsystems (Phases 3-9)
        self.intelligence_router = IntelligenceRouter()
        self.context_memory = ContextMemory()
        self.grounding_gate = GroundingGate()
        self.identity_resolver = IdentityResolver()
        self.timeline_parser = TimelineParser()
        self.stitcher = CrossChannelStitcher()
        self.batch_processor = BatchProcessor()
        self.frame_queue = FrameQueue(max_depth=5)

        # State tracking
        self.current_window: Optional[WindowInfo] = None
        self.current_browser_context: Dict[str, Any] = {}
        self._is_flushing = False
        self._is_heartbeating = False

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
        self.settings_window = SettingsWindow(self.backend_client, self.local_queue, auto_updater=self.updater)

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
        self.bridge.candidate_card_updated.connect(self._handle_candidate_card_update)
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
        self.main_window.toggle_pause_requested.connect(self.toggle_pause)
        self.main_window.sync_now_requested.connect(self._flush_queue_to_backend)

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
        # 1. Window Monitor Timer (polls active window every 600ms)
        self.window_timer = QTimer()
        self.window_timer.timeout.connect(self._poll_active_window)
        self.window_timer.start(600)

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

    def _check_and_consume_installation_claim(self) -> bool:
        """
        Checks for a short-lived installation claim passed via:
        1. Deep link protocol: talentopsscout://claim?claim_id=CLM-...&claim_secret=...
        2. CLI flags: --claim-id CLM-... --claim-secret ...
        3. Bootstrap file: %TEMP%/talentops_scout_claim.json or %LOCALAPPDATA%/TalentOpsAI/Scout/install_claim.json
        Returns True if claim was successfully consumed and authenticated.
        """
        claim_id = None
        claim_secret = None

        # 1. Check CLI args / deep link
        for i, arg in enumerate(sys.argv[1:]):
            if "talentopsscout://" in arg:
                import urllib.parse
                try:
                    parsed = urllib.parse.urlparse(arg)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if "claim_id" in qs and "claim_secret" in qs:
                        claim_id = qs["claim_id"][0]
                        claim_secret = qs["claim_secret"][0]
                        break
                except Exception as e:
                    logger.debug("Failed to parse claim deep link: %s", e)
            elif arg in ("--claim-id", "-claim") and i + 2 < len(sys.argv):
                claim_id = sys.argv[i + 2]
            elif arg in ("--claim-secret", "-secret") and i + 2 < len(sys.argv):
                claim_secret = sys.argv[i + 2]

        # 2. Check local bootstrap claim files
        candidate_paths = [
            os.path.join(tempfile.gettempdir(), "talentops_scout_claim.json"),
            os.path.join(tempfile.gettempdir(), "talentops_claim.json"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "TalentOpsAI", "Scout", "install_claim.json"),
        ]
        if not (claim_id and claim_secret):
            for c_path in candidate_paths:
                if c_path and os.path.exists(c_path):
                    try:
                        with open(c_path, "r", encoding="utf-8") as f:
                            c_data = json.load(f)
                            if c_data.get("claim_id") and c_data.get("claim_secret"):
                                claim_id = c_data["claim_id"]
                                claim_secret = c_data["claim_secret"]
                                logger.info("Found bootstrap claim in %s: %s", c_path, claim_id)
                                break
                    except Exception as e:
                        logger.debug("Failed reading claim file %s: %s", c_path, e)

        if claim_id and claim_secret:
            logger.info("Auto-consuming installation claim: %s", claim_id)
            ok, data = self.backend_client.register_with_claim(claim_id, claim_secret)
            if ok:
                # Cleanup bootstrap file after consumption
                for c_path in candidate_paths:
                    try:
                        if c_path and os.path.exists(c_path):
                            os.remove(c_path)
                    except Exception:
                        pass
                self._on_activation_complete(data)
                return True
            else:
                logger.warning("Failed to auto-consume installation claim: %s", data.get("error"))

        return False

    def _start_loopback_claim_server(self):
        """
        Starts a background HTTP loopback server on 127.0.0.1:49152.
        Allows the web browser on the download page to push the installation claim
        directly to Scout without requiring any manual typing.
        """
        if getattr(self, "_loopback_server", None):
            return

        from http.server import HTTPServer, BaseHTTPRequestHandler

        app_ref = self

        class LoopbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return  # Silence server log output

            def _send_cors(self, status=200):
                self.send_response(status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Content-Type", "application/json")
                self.end_headers()

            def do_OPTIONS(self):
                self._send_cors(204)

            def do_GET(self):
                if "/handshake" in self.path:
                    self._send_cors(200)
                    resp = {
                        "app": "TalentOps Scout Desktop",
                        "version": "2.0.0",
                        "device_id": app_ref.backend_client.device_id,
                        "status": "REGISTRATION_PENDING" if not app_ref.backend_client.is_authenticated() else "AUTHENTICATED",
                        "is_authenticated": app_ref.backend_client.is_authenticated(),
                    }
                    self.wfile.write(json.dumps(resp).encode("utf-8"))
                else:
                    self._send_cors(404)
                    self.wfile.write(b'{"error": "not found"}')

            def do_POST(self):
                if "/claim" in self.path:
                    try:
                        content_len = int(self.headers.get("Content-Length", 0))
                        body = self.rfile.read(content_len).decode("utf-8")
                        payload = json.loads(body)
                        c_id = payload.get("claim_id")
                        c_sec = payload.get("claim_secret")

                        if not (c_id and c_sec):
                            self._send_cors(400)
                            self.wfile.write(b'{"error": "claim_id and claim_secret required"}')
                            return

                        ok, data = app_ref.backend_client.register_with_claim(c_id, c_sec)
                        if ok:
                            self._send_cors(200)
                            self.wfile.write(json.dumps({
                                "ok": True,
                                "status": "REGISTERED",
                                "user_email": data.get("user_email"),
                                "device_id": data.get("device_id"),
                            }).encode("utf-8"))
                            # Trigger GUI activation completion on Qt main thread
                            QTimer.singleShot(0, lambda: app_ref._on_activation_complete(data))
                        else:
                            self._send_cors(403)
                            self.wfile.write(json.dumps({"ok": False, "error": data.get("error")}).encode("utf-8"))
                    except Exception as err:
                        self._send_cors(500)
                        self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))
                else:
                    self._send_cors(404)
                    self.wfile.write(b'{"error": "not found"}')

        def _run():
            try:
                server = HTTPServer(("127.0.0.1", 49152), LoopbackHandler)
                app_ref._loopback_server = server
                logger.info("⚡ Scout loopback claim listener active on 127.0.0.1:49152")
                while not app_ref.backend_client.is_authenticated():
                    server.handle_request()
                server.server_close()
            except Exception as e:
                logger.debug("Loopback server closed or port unavailable: %s", e)

        threading.Thread(target=_run, daemon=True, name="ScoutLoopbackServer").start()

    def start(self):
        """
        Starts the autonomous desktop scout with visible startup progression:
        STARTING -> CONNECTING -> BACKEND CONNECTED -> WINDOW DETECTED -> SCOUT ACTIVE
        """
        logger.info("🚀 TalentOps Scout Desktop starting...")
        self.tray.show()
        self.edge_handle.show()
        self.main_window.show()

        # Step 0: Check for One-Click Installation Claim or Legacy Code
        claimed = self._check_and_consume_installation_claim()
        if not claimed:
            deep_code = None
            for arg in sys.argv[1:]:
                if "talentopsscout://" in arg and "code=" in arg:
                    import urllib.parse
                    try:
                        parsed = urllib.parse.urlparse(arg)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if "code" in qs:
                            deep_code = qs["code"][0]
                    except Exception as e:
                        logger.debug("Failed to parse deep link: %s", e)
                elif arg.startswith("TOS-"):
                    deep_code = arg

            if deep_code:
                logger.info("Found activation code in launch argument: %s", deep_code)
                self.backend_client.activate_with_code(deep_code)

        # Step 0.5: If unauthenticated, transition to REGISTRATION_PENDING & launch loopback server
        if not self.backend_client.is_authenticated():
            logger.info("Scout unauthenticated: transitioning to REGISTRATION_PENDING state and launching loopback listener")
            self._start_loopback_claim_server()
            self.activation_window = ActivationWindow(self.backend_client, parent=self.main_window)
            self.activation_window.activation_successful.connect(self._on_activation_complete)
            self.activation_window.show()
            self.main_window.update_status_state("REGISTRATION_PENDING")
            self.edge_handle.set_status_state("PENDING")
            self.tray.update_icon_status("PENDING")
            self.bridge.event_logged.emit("REGISTRATION_PENDING", "Waiting for one-click pairing from browser...")

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
            b_ctx = {}
            if win.is_browser:
                b_ctx = self.browser_tracker.resolve_browser_context(win.hwnd, win.title)
                self.current_browser_context = b_ctx

            is_allowed, target_type = is_allowed_scout_target(win, b_ctx)
            self.sampler.set_target_allowed(is_allowed)

            if is_allowed:
                self.main_window.update_status_state(f"ACTIVE ({target_type})")
                self.main_window.ind_window.set_state("DETECTED")
            else:
                self.main_window.update_status_state("RESTING (NON-TARGET)")
                self.main_window.ind_window.set_state("IDLE")

            self.bridge.window_updated.emit(win, b_ctx, is_allowed, target_type)
            self.bridge.event_logged.emit("WINDOW_DETECTED", f"[{win.process_name}] {win.title[:30]}")
            QApplication.processEvents()

        # Step 5: SCOUT ACTIVE / STANDBY
        self.sampler.start(initial_window=self.current_window)
        if self.current_window and self.current_window.is_valid and self.sampler.is_target_allowed:
            self.main_window.update_status_state("ACTIVE")
            self.edge_handle.set_status_state("ACTIVE")
            self.tray.update_icon_status("ACTIVE")
            self.bridge.event_logged.emit("SCOUT_ACTIVE", "Autonomous visual watch loop running")
            self.sampler.trigger_immediate_capture(self.current_window, reason="startup_initial")
        else:
            self.main_window.update_status_state("RESTING (NON-TARGET)")
            self.edge_handle.set_status_state("IDLE")
            self.tray.update_icon_status("IDLE")
            self.bridge.event_logged.emit("SCOUT_RESTING", "Resting — Active window is outside allowed targets")

        # Step 6: Check for recent update notification
        self._check_and_notify_recent_update()

        # Step 7: Global Hotkey & Auto-Updater
        self._init_global_hotkey()
        self.updater.start()

        self._emit_telemetry()

    def _init_global_hotkey(self):
        """Registers system-wide hotkey Ctrl+Shift+S for instant candidate capture."""
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+shift+s", self._on_global_hotkey_pressed)
            logger.info("⚡ Global force-capture hotkey registered (Ctrl + Shift + S)")
        except Exception as e:
            logger.debug("Failed to register global hotkey via keyboard: %s", e)

    def _on_global_hotkey_pressed(self):
        """Callback for Ctrl+Shift+S global hotkey."""
        logger.info("⚡ Global hotkey triggered: Ctrl + Shift + S")
        QTimer.singleShot(0, self.force_capture)

    def _on_update_ready(self, version: str, installer_path: str):
        """Invoked by AutoUpdater when a new installer binary is downloaded and verified."""
        logger.info("Update ready to install: v%s (%s)", version, installer_path)
        self._pending_update_version = version
        self._pending_installer_path = installer_path
        self.bridge.event_logged.emit("UPDATE_READY", f"TalentOps Scout v{version} verified. Preparing safe background installation.")
        # Attempt safe installation or schedule on idle
        self._evaluate_safe_install_point()

    def _on_mandatory_update_required(self, min_version: str, remote_version: str):
        """Invoked when local Scout version is below the minimum allowed version."""
        logger.warning("🚨 [MANDATORY UPDATE] Local v%s < minimum v%s. Pausing network uploads.", CURRENT_VERSION, min_version)
        self._is_update_required = True
        self.main_window.update_status_state("UPDATE_REQUIRED")
        self.edge_handle.set_status_state("UPDATE_REQUIRED")
        self.tray.update_icon_status("PENDING")
        self.bridge.event_logged.emit("UPDATE_REQUIRED", f"Critical update required: v{remote_version} (minimum: v{min_version})")
        try:
            if hasattr(self, "tray") and hasattr(self.tray, "tray"):
                self.tray.tray.showMessage(
                    "Critical Update Required",
                    f"TalentOps Scout v{remote_version} is required. Installing update automatically...",
                    QSystemTrayIcon.Warning,
                    8000
                )
        except Exception as e:
            logger.debug("Tray message error: %s", e)

    def _evaluate_safe_install_point(self):
        """
        Evaluates whether Scout is in a safe idle state to perform autonomous background update:
        1. No active capture or extraction in flight
        2. Sampler is in IDLE, PAUSED, or STANDBY state
        3. Network queue flush worker is not actively uploading
        If safe: triggers `updater.apply_update_and_restart()`
        If busy: schedules a re-check via QTimer when idle
        """
        if not getattr(self, "_pending_installer_path", None):
            return

        is_idle = getattr(self.sampler, "state", "IDLE") in ("IDLE", "PAUSED", "STANDBY")
        is_safe = is_idle and not self._is_flushing

        if is_safe:
            logger.info("⚡ Safe install point reached: Sampler is IDLE. Applying update v%s...", self._pending_update_version)
            self.bridge.event_logged.emit("APPLYING_UPDATE", f"Applying update v{self._pending_update_version} in background...")
            pkg = self._pending_installer_path
            self._pending_installer_path = None
            QTimer.singleShot(500, lambda: self.updater.apply_update_and_restart(pkg))
        else:
            logger.debug("Scout busy (state=%s, flushing=%s). Waiting for safe install point...", getattr(self.sampler, "state", ""), self._is_flushing)
            QTimer.singleShot(10000, self._evaluate_safe_install_point)

    def _check_and_notify_recent_update(self):
        """Checks if Scout just restarted after an autonomous background update."""
        try:
            from .core.paths import get_state_dir
            state_file = os.path.join(get_state_dir(), "update_state.json")
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    st = json.load(f)
                last_state = st.get("current_state")
                if last_state in ("SUCCESS", "APPLYING", "STABLE"):
                    logger.info("🎉 Scout Desktop successfully booted after update to v%s!", CURRENT_VERSION)
                    self.bridge.event_logged.emit("UPDATE_SUCCESS", f"Scout successfully updated to version {CURRENT_VERSION}")
                    self.updater.report_status_to_server(
                        self.backend_client.device_id,
                        status="SUCCESS",
                        target_version=CURRENT_VERSION,
                    )
                    if hasattr(self, "tray") and hasattr(self.tray, "tray"):
                        self.tray.tray.showMessage(
                            "TalentOps Scout Updated",
                            f"Scout updated to {CURRENT_VERSION}",
                            QSystemTrayIcon.Information,
                            4000
                        )
                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump({"current_state": "UP_TO_DATE", "version": CURRENT_VERSION, "updated_at": time.time()}, f)
        except Exception as e:
            logger.debug("Error checking recent update state: %s", e)

    def _poll_active_window(self):
        """Checks foreground window and enforces strict targeting rule (LinkedIn on Chrome or MS Teams only)."""
        try:
            win = self.window_tracker.get_active_window()
            if not win.is_valid:
                return

            has_changed = self.window_tracker.has_active_window_changed(win)
            b_ctx = {}
            if win.is_browser:
                b_ctx = self.browser_tracker.resolve_browser_context(win.hwnd, win.title)
                self.current_browser_context = b_ctx

            is_allowed, target_type = is_allowed_scout_target(win, b_ctx)
            self.sampler.set_target_allowed(is_allowed)

            if has_changed:
                self.current_window = win
                self.sampler.set_current_window(win)

                logger.info("Active window switched: [%s] '%s' (Allowed: %s, Type: %s)",
                            win.process_name, win.title[:40], is_allowed, target_type)
                self.bridge.window_updated.emit(win, b_ctx, is_allowed, target_type)

                if is_allowed:
                    self.bridge.event_logged.emit("TARGET_ACTIVE", f"[{target_type}] {win.title[:35]}")
                    self.sampler.trigger_immediate_capture(win, reason="window_changed")
                else:
                    self.bridge.event_logged.emit("TARGET_RESTING", f"Outside allowed target ({target_type})")
        except Exception as e:
            logger.debug("Active window poll error: %s", e)

    def _on_meaningful_frame(self, img: Image.Image, delta: float, win_info: WindowInfo, bbox: Optional[Tuple[int, int, int, int]] = None):
        """
        Invoked by VisualSampler when meaningful visual change occurs.
        Strict Whitelist Gatekeeper: Processes frames from LinkedIn, GitHub, ATS systems, or MS Teams.
        Includes real-time window re-validation to prevent stale win_info race conditions.
        """
        # Gate 1: Check the passed (potentially stale) win_info
        is_allowed, target_type = is_allowed_scout_target(win_info, self.current_browser_context)
        if not is_allowed:
            logger.debug("Frame rejected by strict allowlist gatekeeper: %s", target_type)
            return

        # Gate 2: Real-time foreground window re-validation
        # Prevents race condition where sampler fires with stale LinkedIn win_info
        # but user has already switched to Chat/other tabs
        try:
            live_win = self.window_tracker.get_active_window()
            if live_win and live_win.is_valid:
                live_allowed, live_type = is_allowed_scout_target(live_win, self.current_browser_context)
                if not live_allowed:
                    logger.info("Frame rejected by LIVE window re-check: stale=%s, live=%s (%s)",
                                win_info.title[:30], live_win.title[:30], live_type)
                    return
        except Exception as e:
            logger.debug("Live window re-check failed (proceeding with original): %s", e)

        self.cnt_captured += 1
        capture_id = f"VC-{uuid.uuid4().hex[:6].upper()}"
        b_ctx = self.current_browser_context or {}
        page_url = b_ctx.get("url") or ""
        page_title = b_ctx.get("title") or (win_info.title if win_info else "") or ""
        cand_name = b_ctx.get("candidate_name")

        # Gate 3: URL hard-block — if we have a URL, it MUST be from an allowed domain
        if page_url:
            url_lower = page_url.lower()
            allowed_domains = (
                "linkedin.com", "teams", "github.com",
                "chat.google.com", "mail.google.com",
                "slack.com", "whatsapp.com", "telegram.org",
                "outlook.com", "office.com", "office365.com",
                "stackoverflow.com", "kaggle.com", "dice.com", "wellfound.com", "angel.co",
                "greenhouse.io", "lever.co", "ashbyhq.com", "myworkday.com", "workday.com",
                "icims.com", "smartrecruiters.com",
                ".pdf", "blob:"
            )
            if not any(d in url_lower for d in allowed_domains):
                logger.info("Frame rejected by URL hard-block: %s", page_url[:60])
                return

        # Gate 4: Page title validation — reject Search engine, browser chrome, and non-data pages
        if page_title:
            pt_lower = page_title.lower().strip()
            is_chat_or_doc_window = (
                target_type in ("GOOGLE_CHAT", "TEAMS", "SLACK", "WHATSAPP", "TELEGRAM", "GMAIL", "OUTLOOK", "PDF_RESUME")
                or any(k in (page_url or "").lower() for k in [
                    "chat.google.com", "teams.microsoft.com", "teams.live.com", "app.slack.com",
                    "web.whatsapp.com", "web.telegram.org", "mail.google.com", "outlook.live.com", "outlook.office.com"
                ])
                or pt_lower.endswith(" - chat")
                or " - chat" in pt_lower
                or any(w in pt_lower for w in ["google chat", "microsoft teams", "slack |", "whatsapp", "telegram", "resume", "cv", "curriculum"])
            )
            if not is_chat_or_doc_window:
                disallowed_page_titles = [
                    "google search", "new tab", "extensions",
                    "downloads", "history", "bookmarks",
                ]
                if any(d in pt_lower for d in disallowed_page_titles):
                    logger.info("Frame rejected by page title validation: %s", page_title[:40])
                    return

        # Performance optimization for autonomous periodic scanning:
        # If delta is small (static screen) and we already successfully extracted candidates from this identical view, skip re-OCR
        import hashlib
        img_thumb_hash = hashlib.md5(img.resize((64, 64)).tobytes()).hexdigest()
        is_static_scan = delta <= 0.05
        if (
            is_static_scan
            and hasattr(self, "_last_successful_view_hash")
            and self._last_successful_view_hash == (win_info.title, img_thumb_hash)
        ):
            logger.debug("Autonomous scan: Static view already extracted (%s), skipping duplicate OCR", win_info.title[:30])
            return

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
            ocr_target_path = capture_item.file_path
            if bbox:
                bx1, by1, bx2, by2 = bbox
                box_area = (bx2 - bx1) * (by2 - by1)
                total_area = img.width * img.height
                if total_area > 0 and 0.10 <= (box_area / total_area) <= 0.85:
                    try:
                        crop_img = img.crop(bbox)
                        crop_path = capture_item.file_path.replace(".jpg", "_crop.jpg")
                        crop_img.save(crop_path, "JPEG", quality=85)
                        ocr_target_path = crop_path
                        logger.debug("Running OCR on regional delta crop (%s)", bbox)
                    except Exception as ce:
                        logger.debug("Regional crop failed, falling back to full frame: %s", ce)

            ocr_lines = self.ocr_engine.extract_text_from_image(ocr_target_path)
            if ocr_target_path != capture_item.file_path and os.path.exists(ocr_target_path):
                try:
                    os.remove(ocr_target_path)
                except Exception:
                    pass

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
            self._last_successful_view_hash = (win_info.title, img_thumb_hash)
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

                # Continuous Multi-Hop Cross-Channel Graph Stitching & Peak Enrichment
                try:
                    stitched = self.stitcher.stitch_observation(staged_contact, channel=target_type)
                    staged_contact["completeness_score"] = stitched.completeness_score
                    staged_contact["observed_channels"] = stitched.observed_channels
                    if "metadata_json" in staged_contact and isinstance(staged_contact["metadata_json"], dict):
                        staged_contact["metadata_json"]["completeness_score"] = stitched.completeness_score
                        staged_contact["metadata_json"]["observed_channels"] = stitched.observed_channels
                        staged_contact["metadata_json"]["stitched_entity_id"] = stitched.entity_id
                        if stitched.work_authorization:
                            staged_contact["metadata_json"]["work_authorization"] = stitched.work_authorization
                        if stitched.compensation:
                            staged_contact["metadata_json"]["compensation"] = stitched.compensation
                        if stitched.availability:
                            staged_contact["metadata_json"]["availability"] = stitched.availability
                        if stitched.security_clearance:
                            staged_contact["metadata_json"]["security_clearance"] = stitched.security_clearance

                    # Fill in previously observed fields from earlier hops if missing
                    if not staged_contact.get("email") and stitched.primary_email:
                        staged_contact["email"] = stitched.primary_email
                    if not staged_contact.get("phone") and stitched.primary_phone:
                        staged_contact["phone"] = stitched.primary_phone
                    if not staged_contact.get("linkedin_url") and stitched.linkedin_url:
                        staged_contact["linkedin_url"] = stitched.linkedin_url
                    if not staged_contact.get("company_name") and stitched.current_company:
                        staged_contact["company_name"] = stitched.current_company
                    if not staged_contact.get("title") and stitched.current_title:
                        staged_contact["title"] = stitched.current_title
                except Exception as stitch_err:
                    logger.debug("CrossChannelStitcher error: %s", stitch_err)

                # Data Quality Gate: Validate person name, clean company noise, and check signals
                cand_name = staged_contact.get("recruiter_name") or staged_contact.get("raw_name")
                if c.entity_type != "JOB":
                    if not cand_name or not is_valid_person_name(cand_name):
                        logger.info("Quality Gate: Rejected invalid candidate name '%s'", cand_name)
                        continue

                    # Clean invalid company name to None
                    cur_comp = staged_contact.get("company_name")
                    if cur_comp and not is_valid_company_name(cur_comp):
                        logger.info("Quality Gate: Stripped invalid company noise '%s'", cur_comp)
                        staged_contact["company_name"] = None
                        staged_contact["raw_company"] = ""

                    # Require at least one meaningful signal (title, company, contact, skills, or education)
                    has_signals = bool(
                        staged_contact.get("title")
                        or staged_contact.get("company_name")
                        or staged_contact.get("email")
                        or staged_contact.get("phone")
                        or staged_contact.get("linkedin_url")
                        or staged_contact.get("skills")
                        or staged_contact.get("education")
                    )
                    if not has_signals:
                        logger.info("Quality Gate: Rejected candidate with zero professional signals '%s'", cand_name)
                        continue

                qid = self.local_queue.enqueue_cluster(staged_contact)
                if qid != -1:
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

            # Live Copilot Intelligence Query
            copilot_info = None
            try:
                cand_email = getattr(first, "primary_email", None) or getattr(first, "email", None)
                cand_linkedin = page_url if "linkedin.com/in/" in page_url else getattr(first, "linkedin_url", None)
                copilot_info = self.backend_client.lookup_candidate(
                    name=first.canonical_name,
                    company=first.current_company,
                    linkedin=cand_linkedin,
                    email=cand_email,
                )
                if copilot_info and copilot_info.get("found"):
                    self.cnt_matched += 1
            except Exception as e:
                logger.debug("Live Copilot lookup error: %s", e)

            card_status = "IN DATABASE" if (copilot_info and copilot_info.get("found")) else "STAGED"
            self.bridge.candidate_card_updated.emit(
                first.canonical_name,
                first.current_title or "",
                first.current_company or "",
                first.location or "",
                card_status,
                desc,
                copilot_info
            )
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
        """Dispatches queue flushing to a background thread to eliminate GUI thread freezes."""
        if getattr(self, "_is_flushing", False):
            return
        threading.Thread(
            target=self._async_flush_worker,
            daemon=True,
            name="ScoutBackendSyncWorker"
        ).start()

    def _async_flush_worker(self):
        """Executes HTTP network flush in background worker thread."""
        if not self.backend_client.is_authenticated():
            logger.debug("Database upload deferred: Scout Desktop is in REGISTRATION_PENDING state")
            return

        if getattr(self, "_is_update_required", False):
            logger.warning("Database upload paused: Scout version is below minimum_version. Preserving local SQLite queue.")
            return

        self._is_flushing = True
        try:
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
                if hasattr(self.main_window, "lbl_hero_pill") and self.main_window.lbl_hero_pill.text() == "STAGED":
                    self.main_window.lbl_hero_pill.setText("CLOUD COMMITTED")
                    self.main_window.lbl_hero_pill.setStyleSheet("background: #0F2520; color: #34D399; border: 1px solid #059669; border-radius: 10px; padding: 2px 8px; font-size: 8px; font-weight: 800;")
            else:
                err = res.get("error", "Network error")
                self.local_queue.mark_batch_failed(queue_ids, err)
                self.bridge.event_logged.emit("DB_SYNC_FAILED", f"Error: {err}")
                self.bridge.db_proof_updated.emit("ERROR", res, f"FAILED: {err}")

            self._emit_telemetry()
        except Exception as e:
            logger.debug("Async flush worker error: %s", e)
        finally:
            self._is_flushing = False

    def _send_heartbeat(self):
        """Dispatches heartbeat network request to background thread to eliminate GUI thread freezes."""
        if getattr(self, "_is_heartbeating", False):
            return
        threading.Thread(
            target=self._async_heartbeat_worker,
            daemon=True,
            name="ScoutHeartbeatWorker"
        ).start()

    def _async_heartbeat_worker(self):
        """Executes HTTP heartbeat ping in background worker thread."""
        if not self.backend_client.is_authenticated():
            logger.debug("Heartbeat deferred: Scout Desktop is in REGISTRATION_PENDING state")
            return

        self._is_heartbeating = True
        try:
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
        except Exception as e:
            logger.debug("Async heartbeat error: %s", e)
        finally:
            self._is_heartbeating = False

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

    @Slot(dict)
    def _on_activation_complete(self, data: dict):
        logger.info("Scout successfully activated as user: %s (scout_id: %s)", data.get("user_email"), data.get("scout_id"))
        self.bridge.event_logged.emit("DEVICE_ACTIVATED", f"Connected as {data.get('user_email')}")
        self.main_window.update_status_state("ACTIVE_SAMPLING")
        self._send_heartbeat()

    @Slot(object, dict, bool, str)
    def _handle_window_ui_update(self, win: WindowInfo, b_ctx: dict, is_allowed: bool = True, target_type: str = ""):
        app_name = win.process_name
        title = b_ctx.get("title", win.title)
        url = b_ctx.get("url", "")
        cand = b_ctx.get("candidate_name")
        context_str = f"Candidate: {cand}" if cand else (b_ctx.get("platform") or "Active Screen")
        self.main_window.update_window_context(app_name, title, url, context_str, is_allowed, target_type)
        if is_allowed:
            self.edge_handle.set_status_state("ACTIVE")
            self.tray.update_icon_status("ACTIVE")
        else:
            self.edge_handle.set_status_state("IDLE")
            self.tray.update_icon_status("IDLE")

    @Slot(str, str, str, str, str, str, object)
    def _handle_candidate_card_update(self, name: str, title: str, company: str, location: str, status: str, desc: str, copilot_info: Optional[dict] = None):
        self.main_window.lbl_target_desc.setText(f"Extracted: {desc}")
        self.main_window.update_candidate_card(
            name=name,
            title=title,
            company=company,
            location=location,
            status=status,
            copilot_info=copilot_info
        )

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
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        try:
            if hasattr(self, "updater"):
                self.updater.stop()
        except Exception as e:
            logger.debug("Error stopping updater: %s", e)

        try:
            if hasattr(self, "ocr_engine"):
                self.ocr_engine.close()
        except Exception as e:
            logger.debug("Error closing OCR engine: %s", e)

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
    if sys.platform == "win32":
        # 1. Single-instance guard: Prevent duplicate instances from fighting over resources
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            ERROR_ALREADY_EXISTS = 183
            mutex_name = "Local\\TalentOps_Scout_Desktop_SingleInstance_Mutex"
            h_mutex = kernel32.CreateMutexW(None, True, mutex_name)
            if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                logger.warning("TalentOps Scout is already running. Focusing existing window...")
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, "TalentOps Scout")
                if hwnd:
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                sys.exit(0)
        except Exception as e:
            logger.debug("Mutex check failed: %s", e)

        # 2. Attach to the interactive user desktop and close the open handle immediately
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_default = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_default:
                user32.SetThreadDesktop(h_default)
                user32.CloseDesktop(h_default)
        except Exception as e:
            logger.debug("Failed to set thread desktop: %s", e)

        # 3. Crucial for Windows Taskbar: Set explicit AppUserModelID so Windows taskbar
        # groups and displays the TalentOps logo instead of the generic python.exe icon.
        try:
            import ctypes
            app_id = "TalentOps.Scout.Desktop.Companion"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception as e:
            logger.debug("Failed to set AppUserModelID: %s", e)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    candidate_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "logo.ico")),
        os.path.abspath(r"c:\TalentOpsAI\scout_desktop\assets\logo.ico"),
        os.path.abspath(r"c:\TalentOpsAI\talentops.ico"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "logo.png")),
        os.path.abspath(r"c:\TalentOpsAI\talentops-logo.png"),
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            app_icon = QIcon(p)
            if not app_icon.isNull():
                app.setWindowIcon(app_icon)
                break

    scout = ScoutDesktopApp()
    scout.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
