"""
sync/batch_processor.py — Context-Aware Batch Intelligence Processor

Performs client-side batch optimization before backend submission:
1. Clusters observations belonging to the same entity context
2. Deduplicates semantically identical records within a batch
3. Evaluates information novelty (NEW | ENRICHMENT | DUPLICATE | IGNORE)
4. Scores observation value (relevance × novelty × confidence)
5. Prioritizes batch ordering for maximum backend impact
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger("scout.sync.batch_processor")

@dataclass
class NoveltyResult:
    """Result of evaluating a record's novelty against recently synced items."""
    classification: str  # (NEW | ENRICHMENT | DUPLICATE | IGNORE)
    reason: str
    matched_existing_id: Optional[int] = None

class BatchProcessor:
    """Optimizes batches of observations before syncing to the backend."""

    def __init__(self):
        pass

    def cluster_observations(self, pending: list[dict]) -> list[dict]:
        """Group observations that share the same canonical_name + company_name."""
        clusters: Dict[str, dict] = {}
        
        for obs in pending:
            name = str(obs.get("canonical_name", "")).strip().lower()
            company = str(obs.get("company_name", "")).strip().lower()
            
            if not name:
                continue
                
            key = f"{name}::{company}"
            
            if key not in clusters:
                clusters[key] = obs.copy()
            else:
                # Merge fields, taking non-None values from current obs if they don't exist
                for k, v in obs.items():
                    if v is not None and clusters[key].get(k) is None:
                        clusters[key][k] = v
                        
        return list(clusters.values())

    def deduplicate_batch(self, batch: list[dict]) -> list[dict]:
        """Remove semantically identical records within a batch, keeping highest observation count."""
        unique_records: Dict[str, dict] = {}
        
        for record in batch:
            name = str(record.get("recruiter_name", record.get("canonical_name", ""))).strip().lower()
            company = str(record.get("company_name", "")).strip().lower()
            url = str(record.get("source_url", "")).strip().lower()
            
            if not name:
                continue
                
            key = f"{name}::{company}::{url}"
            
            if key not in unique_records:
                unique_records[key] = record
            else:
                existing_count = unique_records[key].get("observations_count", 0)
                new_count = record.get("observations_count", 0)
                if new_count > existing_count:
                    unique_records[key] = record
                    
        return list(unique_records.values())

    def evaluate_novelty(self, record: dict, recent_synced: list[dict]) -> NoveltyResult:
        """Compare record against recently synced items to determine novelty."""
        if not recent_synced:
            return NoveltyResult("NEW", "No recent sync history")
            
        r_name = str(record.get("canonical_name", "")).strip().lower()
        r_company = str(record.get("company_name", "")).strip().lower()
        r_url = str(record.get("source_url", "")).strip().lower()
        
        if not r_name:
            return NoveltyResult("IGNORE", "Missing entity name")
            
        for synced in recent_synced:
            s_name = str(synced.get("canonical_name", "")).strip().lower()
            s_company = str(synced.get("company_name", "")).strip().lower()
            s_url = str(synced.get("source_url", "")).strip().lower()
            
            if r_name == s_name:
                if r_company == s_company and r_url == s_url and r_url:
                    # Check if fields are identical
                    return NoveltyResult(
                        classification="DUPLICATE",
                        reason="Exact match with recently synced record",
                        matched_existing_id=synced.get("id")
                    )
                else:
                    return NoveltyResult(
                        classification="ENRICHMENT",
                        reason="Matches person but adds new info/context",
                        matched_existing_id=synced.get("id")
                    )
                    
        return NoveltyResult("NEW", "No matching entity found in sync history")

    def evaluate_information_value(self, record: dict) -> float:
        """Calculate the information value score (relevance × confidence)."""
        # Relevance scoring
        relevance = 0.3  # Name only
        
        has_title = bool(record.get("title"))
        has_company = bool(record.get("company_name"))
        has_email = bool(record.get("email"))
        has_phone = bool(record.get("phone"))
        
        if has_email or has_phone:
            relevance = 0.9
        elif has_title and has_company:
            relevance = 0.7
            
        confidence = record.get("confidence", 0.5)
        
        return min(1.0, max(0.0, relevance * confidence))

    def prioritize_batch(self, batch: list[dict]) -> list[dict]:
        """Sort by information value (highest first)."""
        for record in batch:
            record["_info_value"] = self.evaluate_information_value(record)
            
        sorted_batch = sorted(batch, key=lambda x: x.get("_info_value", 0.0), reverse=True)
        
        # Cleanup internal scoring field
        for record in sorted_batch:
            record.pop("_info_value", None)
            
        return sorted_batch

    def process(self, pending: list[dict], recent_synced: list[dict] = None) -> list[dict]:
        """Full pipeline: cluster → deduplicate → evaluate novelty → prioritize."""
        if not pending:
            return []
            
        recent = recent_synced or []
        
        # 1. Cluster
        clustered = self.cluster_observations(pending)
        
        # 2. Deduplicate
        deduped = self.deduplicate_batch(clustered)
        
        # 3. Evaluate Novelty
        processed = []
        for record in deduped:
            novelty = self.evaluate_novelty(record, recent)
            if novelty.classification != "DUPLICATE" and novelty.classification != "IGNORE":
                record["novelty_classification"] = novelty.classification
                processed.append(record)
                
        # 4. Prioritize
        prioritized = self.prioritize_batch(processed)
        
        return prioritized
