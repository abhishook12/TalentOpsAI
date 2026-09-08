"""
scout_desktop/live_ai_bridge.py — Live AI Screenshot Ingestion & Batch Dispatcher

Directly connects live desktop captures to high-fidelity AI analysis and automatically
uploads structured candidate batches to the live TalentOps site (https://talentopsai-1.onrender.com).

Workflow:
1. Watches scout_desktop/captures/ for new screenshot frames.
2. Performs zero-crash sanitized OCR & zone-based logical entity extraction.
3. Validates observations through Evidence Grounding Gate (anti-hallucination).
4. Assembles candidates into staged batches.
5. Automatically uploads batches to the main site via BackendClient.
6. Triggers server-side identity resolution & database promotion (/staging/process-now).
"""

import os
import sys
import time
import json
import glob
import logging
import requests
from typing import List, Dict, Any, Set, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scout_desktop.core.ocr_engine import OcrEngine
from scout_desktop.extractor.entity_extractor import EntityExtractor
from scout_desktop.extractor.grounding_gate import GroundingGate
from scout_desktop.extractor.semantic_factorizer import ProfileJudge, SemanticFactorizer
from scout_desktop.sync.backend_client import BackendClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scout.live_ai_bridge")

# Safe console encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class LiveAIVisionBridge:
    def __init__(
        self,
        captures_dir: Optional[str] = None,
        api_base: Optional[str] = None,
        batch_debounce_sec: float = 3.0,
    ):
        self.captures_dir = captures_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "captures"
        )
        os.makedirs(self.captures_dir, exist_ok=True)
        
        self.ocr_engine = OcrEngine()
        self.extractor = EntityExtractor()
        self.semantic_factorizer = SemanticFactorizer()
        self.grounding_gate = GroundingGate()
        self.backend_client = BackendClient(api_base=api_base)
        
        self.batch_debounce_sec = batch_debounce_sec
        self.processed_files: Set[str] = set()
        self.total_frames_analyzed = 0
        self.total_candidates_extracted = 0
        self.total_batches_uploaded = 0
        self._seed_existing_captures()

    def _seed_existing_captures(self):
        """Marks already-existing old captures so we only process new incoming frames."""
        existing = glob.glob(os.path.join(self.captures_dir, "*.jpg"))
        for f in existing:
            self.processed_files.add(os.path.abspath(f))
        
        print("\n" + "=" * 70)
        print(">> TALENTOPS AI -- LIVE SCREENSHOT INGESTION & UPLOAD PIPELINE")
        print("=" * 70)
        print(f"[*] Target Backend  : {self.backend_client.active_api_base}")
        print(f"[*] Captures Folder : {self.captures_dir}")
        print(f"[*] Seeded Frames   : {len(self.processed_files)} existing frames ignored")
        print("=" * 70 + "\n")

    def analyze_capture(self, image_path: str) -> List[Dict[str, Any]]:
        """Extracts high-fidelity candidate data from a single screenshot."""
        capture_id = os.path.splitext(os.path.basename(image_path))[0]
        self.total_frames_analyzed += 1
        
        # 1. OCR Extraction with control character sanitization
        lines = self.ocr_engine.extract_text_from_image(image_path)
        if not lines:
            return []

        # 2. Intelligent AI Triage: Judge if the frame is a candidate profile
        judgment = ProfileJudge.judge_frame(lines, window_title="Live Screen Frame")
        if not judgment.is_candidate_profile:
            now_str = time.strftime("%H:%M:%S")
            print(f"[{now_str}] [-] [TRIAGE DISCARD] Frame '{os.path.basename(image_path)}' rejected: {judgment.category} ({judgment.rejection_reason})")
            return []

        # 3. Deep AI Semantic Factorization
        factorized = self.semantic_factorizer.factorize(
            lines=lines,
            window_title="TalentOps Live Candidate",
            source_url="https://www.linkedin.com/in/live-profile/",
            capture_id=capture_id,
        )

        staged_contacts = []
        if factorized:
            contact = factorized.to_staged_dict()
            staged_contacts.append(contact)
            self.total_candidates_extracted += 1

            # Print rich factorized live card
            now_str = time.strftime("%H:%M:%S")
            print(f"\n+-- [AI FACTORIZED CANDIDATE] --------------------------------------------")
            print(f"| Frame File   : {os.path.basename(image_path)} ({now_str})")
            print(f"| Candidate    : {factorized.canonical_name}" + (f" ({factorized.pronouns})" if factorized.pronouns else ""))
            print(f"| Active Title : {factorized.current_title or 'N/A'}")
            print(f"| Employer     : {factorized.current_company or 'N/A'}")
            if factorized.previous_company or factorized.previous_title:
                prev = f"{factorized.previous_title or ''} at {factorized.previous_company or ''}".strip(" at ")
                print(f"| Previous Role: {prev}")
            print(f"| Location     : {factorized.location or 'N/A'}")
            print(f"| Education    : {factorized.education or 'N/A'}")
            skills_preview = ", ".join(factorized.skills[:4]) + (f" (+{len(factorized.skills)-4} more)" if len(factorized.skills) > 4 else "")
            print(f"| Skills       : {skills_preview or 'None'}")
            print(f"| AI Quality   : {factorized.quality_score}/100 | Confidence: {int(factorized.identity_confidence * 100)}%")
            print(f"+-----------------------------------------------------------------------")
        else:
            # Fallback to zone extractor if passes validation
            clusters = self.extractor.extract_from_lines(
                lines=lines,
                capture_id=capture_id,
                source_url="https://www.linkedin.com/in/live-profile/",
                window_title="TalentOps Scout Live Capture",
            )
            for c in clusters:
                contact = c.to_staged_contact_dict()
                name = contact.get("recruiter_name")
                if name and is_valid_person_name(name):
                    staged_contacts.append(contact)
                    self.total_candidates_extracted += 1

        return staged_contacts

    def upload_batch(self, contacts: List[Dict[str, Any]]) -> bool:
        """Uploads candidate batch to the main site and triggers promotion."""
        if not contacts:
            return True

        print(f"\n>> Dispatching batch of {len(contacts)} candidate(s) to production site...")
        success, resp = self.backend_client.sync_staged_batch(contacts)
        
        if success:
            self.total_batches_uploaded += 1
            batch_id = resp.get("batch_id", "N/A")
            staged_cnt = resp.get("staged", len(contacts))
            print(f"[+] BATCH UPLOAD SUCCESS: Batch ID [{batch_id}] | Staged: {staged_cnt}")
            self._trigger_server_promotion()
            print(f"[*] [LIVE TELEMETRY] Frames: {self.total_frames_analyzed} | Candidates: {self.total_candidates_extracted} | Batches Uploaded: {self.total_batches_uploaded}\n")
            return True
        else:
            print(f"[-] Batch upload FAILED: {resp}")
            return False

    def _trigger_server_promotion(self):
        """Calls /staging/process-now to immediately resolve and promote to recruiters table."""
        try:
            url = f"{self.backend_client.active_api_base}/staging/process-now"
            headers = self.backend_client._get_headers()
            res = requests.post(url, headers=headers, timeout=5.0)
            if res.status_code == 200:
                print(f"[*] Server batch promotion complete: {res.json().get('stats', {})}")
        except Exception as e:
            pass

    def process_pending_once(self) -> int:
        """Scans for new capture files and processes them in a batch."""
        all_files = glob.glob(os.path.join(self.captures_dir, "*.jpg"))
        unprocessed = [os.path.abspath(f) for f in all_files if os.path.abspath(f) not in self.processed_files]
        
        if not unprocessed:
            return 0

        unprocessed.sort(key=lambda p: os.path.getmtime(p))
        batch_contacts = []
        for img in unprocessed:
            self.processed_files.add(img)
            contacts = self.analyze_capture(img)
            batch_contacts.extend(contacts)

        if batch_contacts:
            self.upload_batch(batch_contacts)

        return len(unprocessed)

    def run_live_loop(self, poll_interval: float = 1.5):
        """Continuously watches for incoming captures and uploads batches live."""
        print("[*] [AI BRIDGE ACTIVE] Listening for new screen captures in real-time...")
        print("   (To pause or stop, press Ctrl+C in this window)\n")
        last_heartbeat = time.time()
        try:
            while True:
                found = self.process_pending_once()
                now = time.time()
                # Print periodic heartbeat every 8 seconds if idle
                if not found and (now - last_heartbeat) >= 8.0:
                    ts = time.strftime("%H:%M:%S")
                    print(f"[{ts}] [*] [ACTIVE & LISTENING] Watching {self.captures_dir} (0 new frames)...")
                    last_heartbeat = now
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n[!] Live AI Bridge stopped.")


if __name__ == "__main__":
    bridge = LiveAIVisionBridge()
    bridge.run_live_loop()
