"""
TalentOpsAI Deep SMTP Mailbox Ping Verification Engine
=======================================================
Performs non-intrusive SMTP RCPT TO handshake probes to verify whether
a specific mailbox exists at the destination mail server — without
actually sending any email.

Protocol flow:
  1. EHLO talentops.ai
  2. MAIL FROM:<probe@talentops.ai>
  3. RCPT TO:<target@domain.com>
  4. Interpret response code:
     - 250 → mailbox exists
     - 550/551/552/553 → mailbox does not exist
     - 450/451/452 → greylisted / rate-limited (treat as catch-all)
     - Timeout → inconclusive
  5. QUIT (never send DATA)

Safety:
  - Never sends email content (no DATA command)
  - Rate-limited to avoid blacklisting
  - Connection pooling per MX host
  - Cached results to prevent re-probing
"""

import os
import json
import time
import socket
import smtplib
import logging
import threading
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from dataclasses import dataclass, asdict

logger = logging.getLogger("smtp_prober")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PROBE_CACHE_FILE = os.path.join(DATA_DIR, "smtp_probe_cache.json")
CATCHALL_CACHE_FILE = os.path.join(DATA_DIR, "catchall_domain_cache.json")

PROBE_SENDER = "probe@talentops.ai"
PROBE_EHLO_DOMAIN = "talentops.ai"
PROBE_TIMEOUT = 10  # seconds per connection
MAX_CONCURRENT_PROBES = 50
RATE_LIMIT_PER_DOMAIN = 0.5  # seconds between probes to same MX host


@dataclass
class SmtpProbeResult:
    """Result of an SMTP mailbox probe."""
    email: str
    smtp_code: int           # 250, 550, 450, 0 (timeout/error)
    smtp_message: str
    mailbox_exists: bool     # True if 250
    is_catchall: bool        # True if domain accepts all
    is_greylisted: bool      # True if 450/451/452
    confidence_delta: int    # How much to adjust confidence
    probe_time_ms: float
    probed_at: str
    mx_host: str


class SmtpProber:
    """
    High-throughput SMTP RCPT TO mailbox verification engine.
    
    Features:
      - Probes individual mailboxes via SMTP handshake (no email sent)
      - Detects catch-all domains (accepts any random address)
      - Caches results to prevent re-probing
      - Thread-safe with connection pooling
      - Rate-limited per MX host
    """

    def __init__(self):
        self._probe_cache: Dict[str, dict] = {}
        self._catchall_cache: Dict[str, bool] = {}
        self._domain_last_probe: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._load_caches()

    # ─── Cache Management ────────────────────────────────────────────────────

    def _load_caches(self):
        """Load probe and catch-all caches from disk."""
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(PROBE_CACHE_FILE):
            try:
                with open(PROBE_CACHE_FILE, 'r') as f:
                    self._probe_cache = json.load(f)
                logger.info(f"Loaded {len(self._probe_cache)} cached SMTP probe results")
            except Exception as e:
                logger.warning(f"Failed to load probe cache: {e}")

        if os.path.exists(CATCHALL_CACHE_FILE):
            try:
                with open(CATCHALL_CACHE_FILE, 'r') as f:
                    self._catchall_cache = json.load(f)
                logger.info(f"Loaded {len(self._catchall_cache)} cached catch-all domain results")
            except Exception as e:
                logger.warning(f"Failed to load catch-all cache: {e}")

    def _save_probe_cache(self):
        """Persist probe results to disk."""
        try:
            with open(PROBE_CACHE_FILE, 'w') as f:
                json.dump(self._probe_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save probe cache: {e}")

    def _save_catchall_cache(self):
        """Persist catch-all detection results to disk."""
        try:
            with open(CATCHALL_CACHE_FILE, 'w') as f:
                json.dump(self._catchall_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save catch-all cache: {e}")

    # ─── MX Resolution ───────────────────────────────────────────────────────

    def _get_mx_host(self, domain: str) -> Optional[str]:
        """Resolve the primary MX host for a domain."""
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, 'MX')
            if answers:
                # Sort by preference (lowest = highest priority)
                mx_records = sorted(answers, key=lambda r: r.preference)
                return str(mx_records[0].exchange).rstrip('.').lower()
        except Exception:
            pass
        return None

    # ─── Rate Limiting ───────────────────────────────────────────────────────

    def _wait_for_rate_limit(self, mx_host: str):
        """Enforce per-host rate limiting to avoid blacklisting."""
        with self._lock:
            last_probe = self._domain_last_probe.get(mx_host, 0)
            elapsed = time.time() - last_probe
            if elapsed < RATE_LIMIT_PER_DOMAIN:
                time.sleep(RATE_LIMIT_PER_DOMAIN - elapsed)
            self._domain_last_probe[mx_host] = time.time()

    # ─── Catch-All Detection ─────────────────────────────────────────────────

    def detect_catchall(self, domain: str) -> bool:
        """
        Detect if a domain is a catch-all by probing a random non-existent address.
        A catch-all domain accepts RCPT TO for any address, making individual
        mailbox verification unreliable.
        """
        if domain in self._catchall_cache:
            return self._catchall_cache[domain]

        # Generate a random probe address that is extremely unlikely to exist
        random_local = f"zz-nonexist-{hashlib.md5(domain.encode()).hexdigest()[:8]}"
        probe_email = f"{random_local}@{domain}"

        mx_host = self._get_mx_host(domain)
        if not mx_host:
            return False

        try:
            self._wait_for_rate_limit(mx_host)
            server = smtplib.SMTP(timeout=PROBE_TIMEOUT)
            server.connect(mx_host, 25)
            server.ehlo(PROBE_EHLO_DOMAIN)
            try:
                server.starttls()
                server.ehlo(PROBE_EHLO_DOMAIN)
            except smtplib.SMTPNotSupportedError:
                pass  # TLS not required

            server.mail(PROBE_SENDER)
            code, msg = server.rcpt(probe_email)
            server.quit()

            is_catchall = code == 250
            with self._lock:
                self._catchall_cache[domain] = is_catchall
                self._save_catchall_cache()

            if is_catchall:
                logger.info(f"Domain {domain} detected as catch-all (accepts any address)")
            return is_catchall

        except Exception as e:
            logger.debug(f"Catch-all detection failed for {domain}: {e}")
            return False

    # ─── Single Email Probe ──────────────────────────────────────────────────

    def probe_mailbox(self, email: str, mx_host: Optional[str] = None) -> SmtpProbeResult:
        """
        Probe a single mailbox via SMTP RCPT TO handshake.
        Returns a SmtpProbeResult with the SMTP response code and confidence delta.
        """
        email = email.lower().strip()
        start_time = time.time()

        # Check cache first
        if email in self._probe_cache:
            cached = self._probe_cache[email]
            return SmtpProbeResult(**cached)

        domain = email.split('@')[1] if '@' in email else ''
        if not domain:
            return SmtpProbeResult(
                email=email, smtp_code=0, smtp_message="Invalid email format",
                mailbox_exists=False, is_catchall=False, is_greylisted=False,
                confidence_delta=-20, probe_time_ms=0, probed_at=datetime.now(timezone.utc).isoformat(),
                mx_host=""
            )

        # Resolve MX if not provided
        if not mx_host:
            mx_host = self._get_mx_host(domain)
        if not mx_host:
            elapsed = (time.time() - start_time) * 1000
            return SmtpProbeResult(
                email=email, smtp_code=0, smtp_message="No MX host resolved",
                mailbox_exists=False, is_catchall=False, is_greylisted=False,
                confidence_delta=-15, probe_time_ms=elapsed,
                probed_at=datetime.now(timezone.utc).isoformat(), mx_host=""
            )

        # Check catch-all status
        is_catchall = self.detect_catchall(domain)

        # Rate limit
        self._wait_for_rate_limit(mx_host)

        smtp_code = 0
        smtp_message = ""
        mailbox_exists = False
        is_greylisted = False
        confidence_delta = 0

        try:
            server = smtplib.SMTP(timeout=PROBE_TIMEOUT)
            server.connect(mx_host, 25)
            server.ehlo(PROBE_EHLO_DOMAIN)
            try:
                server.starttls()
                server.ehlo(PROBE_EHLO_DOMAIN)
            except smtplib.SMTPNotSupportedError:
                pass

            server.mail(PROBE_SENDER)
            code, msg = server.rcpt(email)
            smtp_code = code
            smtp_message = msg.decode('utf-8', errors='replace') if isinstance(msg, bytes) else str(msg)
            server.quit()

            if code == 250:
                if is_catchall:
                    mailbox_exists = True
                    confidence_delta = 5  # Catch-all domains accept everything, low signal
                else:
                    mailbox_exists = True
                    confidence_delta = 25  # Strong positive signal
            elif code in (550, 551, 552, 553):
                mailbox_exists = False
                confidence_delta = -40  # Strong negative signal — mailbox rejected
            elif code in (450, 451, 452):
                is_greylisted = True
                confidence_delta = 0  # Inconclusive — greylisting or rate limiting
            else:
                confidence_delta = 0  # Unknown response

        except smtplib.SMTPConnectError:
            smtp_message = "Connection refused"
            confidence_delta = 0  # Can't determine
        except smtplib.SMTPServerDisconnected:
            smtp_message = "Server disconnected"
            confidence_delta = 0
        except socket.timeout:
            smtp_message = "Connection timed out"
            confidence_delta = 0
        except Exception as e:
            smtp_message = str(e)
            confidence_delta = 0

        elapsed = (time.time() - start_time) * 1000

        result = SmtpProbeResult(
            email=email,
            smtp_code=smtp_code,
            smtp_message=smtp_message,
            mailbox_exists=mailbox_exists,
            is_catchall=is_catchall,
            is_greylisted=is_greylisted,
            confidence_delta=confidence_delta,
            probe_time_ms=round(elapsed, 1),
            probed_at=datetime.now(timezone.utc).isoformat(),
            mx_host=mx_host
        )

        # Cache the result
        with self._lock:
            self._probe_cache[email] = asdict(result)
            # Periodic save (every 100 new probes)
            if len(self._probe_cache) % 100 == 0:
                self._save_probe_cache()

        return result

    # ─── Batch Probing ───────────────────────────────────────────────────────

    def probe_batch(self, emails: list[str], max_workers: int = None) -> list[SmtpProbeResult]:
        """
        Probe multiple mailboxes concurrently with rate limiting.
        Returns list of SmtpProbeResult for each email.
        """
        if max_workers is None:
            max_workers = min(MAX_CONCURRENT_PROBES, len(emails))

        results = []
        
        # Pre-resolve MX hosts and group emails by domain
        domain_mx: Dict[str, str] = {}
        for email in emails:
            domain = email.split('@')[1] if '@' in email else ''
            if domain and domain not in domain_mx:
                mx = self._get_mx_host(domain)
                if mx:
                    domain_mx[domain] = mx

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for email in emails:
                domain = email.split('@')[1] if '@' in email else ''
                mx_host = domain_mx.get(domain)
                future = executor.submit(self.probe_mailbox, email, mx_host)
                futures[future] = email

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    email = futures[future]
                    logger.error(f"Probe failed for {email}: {e}")
                    results.append(SmtpProbeResult(
                        email=email, smtp_code=0, smtp_message=str(e),
                        mailbox_exists=False, is_catchall=False, is_greylisted=False,
                        confidence_delta=0, probe_time_ms=0,
                        probed_at=datetime.now(timezone.utc).isoformat(), mx_host=""
                    ))

        # Final cache save
        self._save_probe_cache()
        return results

    # ─── Statistics ──────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return probe cache statistics."""
        total = len(self._probe_cache)
        exists = sum(1 for v in self._probe_cache.values() if v.get('mailbox_exists'))
        rejected = sum(1 for v in self._probe_cache.values() if v.get('smtp_code') in (550, 551, 552, 553))
        catchall = sum(1 for v in self._probe_cache.values() if v.get('is_catchall'))
        greylisted = sum(1 for v in self._probe_cache.values() if v.get('is_greylisted'))
        domains_checked = len(self._catchall_cache)
        catchall_domains = sum(1 for v in self._catchall_cache.values() if v)

        return {
            "total_probed": total,
            "mailbox_exists": exists,
            "mailbox_rejected": rejected,
            "catchall_responses": catchall,
            "greylisted": greylisted,
            "domains_checked_catchall": domains_checked,
            "catchall_domains": catchall_domains,
            "cache_file": PROBE_CACHE_FILE
        }

    def clear_cache(self):
        """Clear all cached probe results."""
        with self._lock:
            self._probe_cache.clear()
            self._catchall_cache.clear()
            self._save_probe_cache()
            self._save_catchall_cache()


# Module-level singleton
smtp_prober = SmtpProber()
