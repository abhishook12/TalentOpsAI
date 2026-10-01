"""
scout_desktop/extractor/adaptive_reflex_engine.py

Frontier 5: Self-Evolving Code (Self-Healing DOM & Extraction Reflexes)
======================================================================
Autonomous reflex learning engine that observes layout drift and DOM changes.
When standard hardcoded selectors or regex fail to extract a candidate (or confidence < 0.75),
the Adaptive Reflex Engine analyzes spatial line topology, synthesizes a new
extraction reflex rule, persists it to adaptive_rules.json, and hot-reloads it in-memory
for sub-millisecond future execution without application restarts.
"""

import os
import re
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from .patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_job_title,
    is_plausible_title,
    clean_company_name,
    is_valid_company_name,
)
from .neural_lexicon_repair import lexicon_repair

logger = logging.getLogger("scout.adaptive_reflex")

RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adaptive_rules.json")


class AdaptiveReflexEngine:
    """
    Self-calibrating and self-healing extraction reflex engine.
    Learns and adapts to website DOM redesigns automatically.
    """

    def __init__(self, rules_path: Optional[str] = None):
        self.rules_path = rules_path or RULES_FILE
        self._rules: List[Dict[str, Any]] = []
        self._stats = {
            "heals_performed": 0,
            "rules_synthesized": 0,
            "rules_loaded": 0,
            "failed_attempts": 0,
        }
        self.load_rules()

    def load_rules(self):
        """Loads persistent adaptive rules from disk."""
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._rules = data
                    elif isinstance(data, dict) and "rules" in data:
                        self._rules = data["rules"]
                self._stats["rules_loaded"] = len(self._rules)
                logger.info("[ADAPTIVE_REFLEX] Loaded %d persistent adaptive rules", len(self._rules))
            except Exception as e:
                logger.warning("[ADAPTIVE_REFLEX] Error reading %s: %s", self.rules_path, e)
                self._rules = []
        else:
            self._rules = []
            self.save_rules()

    def save_rules(self):
        """Persists learned rules to disk."""
        try:
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(self._rules, f, indent=2)
        except Exception as e:
            logger.warning("[ADAPTIVE_REFLEX] Error saving rules to %s: %s", self.rules_path, e)

    def heal_frame(
        self,
        ocr_lines: List[str],
        window_title: str = "",
        source_url: str = "",
        platform: str = "",
        current_name: Optional[str] = None,
        current_title: Optional[str] = None,
        current_company: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts to self-heal a candidate frame using existing learned reflexes
        or topological reflex synthesis.
        """
        if not ocr_lines or len(ocr_lines) < 2:
            return None

        # 1. Try existing learned reflex rules first (Fast Path)
        for rule in self._rules:
            if platform and rule.get("platform") and rule["platform"].lower() != platform.lower():
                continue

            # Check window title regex if present
            win_pat = rule.get("window_pattern")
            if win_pat and window_title and not re.search(win_pat, window_title, re.IGNORECASE):
                continue

            # Evaluate rule on lines
            healed = self._apply_rule(rule, ocr_lines)
            if healed:
                rule["hit_count"] = rule.get("hit_count", 0) + 1
                rule["last_hit_at"] = time.time()
                self._stats["heals_performed"] += 1
                self.save_rules()
                logger.info(
                    "🎯 [ADAPTIVE_REFLEX] Healed frame via rule '%s': %s (%s)",
                    rule.get("rule_id"), healed.get("canonical_name"), healed.get("title")
                )
                return healed

        # 2. Reflex Discovery: Analyze layout topology to discover new layout pattern
        discovered = self._synthesize_reflex_from_topology(
            ocr_lines=ocr_lines,
            window_title=window_title,
            platform=platform,
            known_name=current_name,
            known_title=current_title,
            known_company=current_company,
        )

        if discovered:
            self._stats["heals_performed"] += 1
            self._stats["rules_synthesized"] += 1
            return discovered

        self._stats["failed_attempts"] += 1
        return None

    def _apply_rule(self, rule: Dict[str, Any], lines: List[str]) -> Optional[Dict[str, Any]]:
        """Evaluates an existing adaptive rule against visible lines."""
        try:
            name_idx = rule.get("name_line_idx")
            title_idx = rule.get("title_line_idx")

            name = None
            if name_idx is not None and 0 <= name_idx < len(lines):
                cand = clean_person_name(lines[name_idx])
                if cand and is_valid_person_name(cand):
                    name = cand

            if not name:
                # Try name regex anchor if specified
                name_regex = rule.get("name_regex")
                if name_regex:
                    for line in lines[:10]:
                        m = re.search(name_regex, line)
                        if m:
                            cand = clean_person_name(m.group(1) if m.groups() else line)
                            if cand and is_valid_person_name(cand):
                                name = cand
                                break

            if not name:
                return None

            title = None
            company = None
            if title_idx is not None and 0 <= title_idx < len(lines):
                t_raw = lines[title_idx]
                t_clean = clean_job_title(t_raw)
                if t_clean:
                    rep_t, score = lexicon_repair.repair_title(t_clean)
                    if score >= 0.78:
                        title = rep_t
                    elif is_plausible_title(t_clean):
                        title = t_clean

            # If company index exists
            comp_idx = rule.get("company_line_idx")
            if comp_idx is not None and 0 <= comp_idx < len(lines):
                c_clean = clean_company_name(lines[comp_idx])
                if c_clean and is_valid_company_name(c_clean):
                    company = c_clean

            return {
                "canonical_name": name,
                "title": title or "Talent Acquisition Specialist",
                "company": company,
                "confidence": 0.88,
                "evidence": f"Adaptive Learned Reflex ({rule.get('rule_id', 'unknown')})",
                "rule_id": rule.get("rule_id"),
                "is_adaptive_healed": True,
            }
        except Exception as e:
            logger.debug("[ADAPTIVE_REFLEX] Rule execution failed: %s", e)
            return None

    def _synthesize_reflex_from_topology(
        self,
        ocr_lines: List[str],
        window_title: str,
        platform: str,
        known_name: Optional[str] = None,
        known_title: Optional[str] = None,
        known_company: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Deep topological scanner that discovers candidate structure in unfamiliar layouts.
        """
        from .field_classifier import FieldClassifier

        discovered_name = None
        discovered_name_idx = None
        discovered_title = None
        discovered_title_idx = None
        discovered_company = None
        discovered_comp_idx = None

        # Pass A: Find Candidate Name in top 8 non-noise lines
        for idx, line in enumerate(ocr_lines[:8]):
            if FieldClassifier.is_ui_noise(line):
                continue

            cleaned = clean_person_name(line)
            if cleaned and is_valid_person_name(cleaned):
                # Extra check: ensure not equal to platform name or window title noise
                if platform and platform.lower() in cleaned.lower():
                    continue
                discovered_name = cleaned
                discovered_name_idx = idx
                break

        if not discovered_name and known_name and is_valid_person_name(known_name):
            discovered_name = known_name

        if not discovered_name:
            return None

        # Pass B: Find Candidate Title in lines following discovered name
        start_search = (discovered_name_idx + 1) if discovered_name_idx is not None else 0
        end_search = min(start_search + 5, len(ocr_lines))

        for idx in range(start_search, end_search):
            line = ocr_lines[idx]
            if FieldClassifier.is_ui_noise(line):
                continue

            # Check if line contains title @ company
            if "@" in line or " at " in line:
                t_cand, c_cand = FieldClassifier.extract_title_and_company(
                    headline_lines=[line], header_lines=[], experience_lines=[]
                )[:3:2]
                if t_cand:
                    discovered_title = t_cand
                    discovered_title_idx = idx
                if c_cand:
                    discovered_company = c_cand
                    discovered_comp_idx = idx
                if discovered_title:
                    break

            # Check standalone title
            t_cand = clean_job_title(line)
            if t_cand:
                rep_t, score = lexicon_repair.repair_title(t_cand)
                if score >= 0.78:
                    discovered_title = rep_t
                    discovered_title_idx = idx
                    break
                elif is_plausible_title(t_cand):
                    discovered_title = t_cand
                    discovered_title_idx = idx
                    break

        if not discovered_title and known_title:
            discovered_title = known_title

        if not discovered_title:
            discovered_title = "Talent Acquisition Specialist"

        # Pass C: Synthesize & Persist Novel Rule
        rule_id = f"reflex_{platform or 'generic'}_{len(self._rules) + 1}_{int(time.time())}"
        win_pat = re.escape(window_title.split("-")[0].strip()) if window_title else None

        new_rule = {
            "rule_id": rule_id,
            "platform": platform or "unknown",
            "window_pattern": win_pat,
            "name_line_idx": discovered_name_idx,
            "title_line_idx": discovered_title_idx,
            "company_line_idx": discovered_comp_idx,
            "name_sample": discovered_name,
            "title_sample": discovered_title,
            "created_at": time.time(),
            "hit_count": 1,
            "last_hit_at": time.time(),
        }

        self._rules.append(new_rule)
        self.save_rules()
        logger.info(
            "⚡ [ADAPTIVE_REFLEX] Synthesized and hot-reloaded adaptive reflex rule '%s' "
            "for candidate '%s' (%s)",
            rule_id, discovered_name, discovered_title
        )

        return {
            "canonical_name": discovered_name,
            "title": discovered_title,
            "company": discovered_company or known_company,
            "confidence": 0.85,
            "evidence": f"Synthesized Adaptive Reflex ({rule_id})",
            "rule_id": rule_id,
            "is_adaptive_healed": True,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Telemetry and metrics for fleet reporting."""
        return {
            "rules_count": len(self._rules),
            **self._stats,
            "rules_summary": [
                {
                    "rule_id": r.get("rule_id"),
                    "platform": r.get("platform"),
                    "hit_count": r.get("hit_count", 0),
                    "title_sample": r.get("title_sample"),
                }
                for r in self._rules[-5:]  # Return latest 5
            ],
        }


# Singleton export
adaptive_reflex_engine = AdaptiveReflexEngine()
