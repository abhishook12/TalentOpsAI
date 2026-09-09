"""
TalentOps Scout 2.0 - Provenance & Defense Audit Ledger
Generates and verifies cryptographic provenance metadata for all
edge observations to ensure data integrity, authorized lineage, and non-repudiation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import socket
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("scout.provenance")


class ProvenanceLedger:
    """
    Creates immutable provenance records accompanying observations sent to the Knowledge Graph.
    Ensures full auditability of what, when, how, and why an edge signal was derived.
    """

    _sequence_counter = 0

    @classmethod
    def _get_node_identifier(cls) -> str:
        """Returns stable machine identifier."""
        try:
            return f"{socket.gethostname()}-{platform.system().lower()}"
        except Exception:
            return "scout-node-default"

    @classmethod
    def generate_provenance(
        cls,
        observation_id: str,
        source_domain: str,
        scope_authorization: str,
        content_payload: dict[str, Any],
        confidence: float = 0.95,
        extractor_version: str = "2.0.0",
        model_version: str = "talentops-edge-v2",
    ) -> dict[str, Any]:
        """
        Generate cryptographic provenance record for an observation or packet.
        """
        cls._sequence_counter += 1
        now_ts = time.time()

        # Compute SHA-256 hash of the normalized content payload
        try:
            payload_str = json.dumps(content_payload, sort_keys=True, default=str)
        except Exception:
            payload_str = str(content_payload)
        content_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        node_id = cls._get_node_identifier()

        # Compute tamper-evident lineage checksum
        lineage_input = f"{observation_id}|{source_domain}|{scope_authorization}|{content_hash}|{now_ts}|{node_id}"
        provenance_signature = hashlib.sha256(lineage_input.encode("utf-8")).hexdigest()

        return {
            "observation_id": observation_id,
            "sequence_number": cls._sequence_counter,
            "captured_at": now_ts,
            "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts)),
            "source_domain": source_domain,
            "scope_authorization": scope_authorization,
            "edge_node_id": node_id,
            "content_sha256": content_hash,
            "extractor_version": extractor_version,
            "model_version": model_version,
            "confidence_score": confidence,
            "lineage_signature": provenance_signature,
            "legal_boundary": "AUTHORIZED_PASSIVE_OBSERVATION",
        }

    @classmethod
    def verify_provenance(cls, record: dict[str, Any], content_payload: dict[str, Any]) -> bool:
        """
        Validates that an observation's provenance block matches its payload and signature.
        """
        try:
            stored_hash = record.get("content_sha256")
            payload_str = json.dumps(content_payload, sort_keys=True, default=str)
            computed_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            if stored_hash != computed_hash:
                logger.warning("Provenance content hash mismatch: expected %s, got %s", stored_hash, computed_hash)
                return False

            observation_id = record.get("observation_id", "")
            source_domain = record.get("source_domain", "")
            scope_authorization = record.get("scope_authorization", "")
            captured_at = record.get("captured_at", 0)
            node_id = record.get("edge_node_id", "")
            stored_sig = record.get("lineage_signature", "")

            expected_sig = hashlib.sha256(
                f"{observation_id}|{source_domain}|{scope_authorization}|{computed_hash}|{captured_at}|{node_id}".encode("utf-8")
            ).hexdigest()

            return stored_sig == expected_sig
        except Exception as e:
            logger.error("Error verifying provenance: %s", e)
            return False
