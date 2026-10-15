"""
SheetTargetSeeder — Permanent Sheet-by-Sheet Target Seeder for TalentOps AI.
=============================================================================
Manages systematic, ordered company harvesting from user-supplied workbooks
(media_1791206573787.xlsx: Ritik -> Anek -> Suhani).

Enforces the User Mandate:
1. Harvests every company in Sheet 1 ('Ritik') first.
2. Moves to Sheet 2 ('Anek') once Sheet 1 is completed.
3. Moves to Sheet 3 ('Suhani') once Sheet 2 is completed.
4. Only after all 3 sheets are fully completed does it release the harvester
   to continue on global targets (Parquet 437k, ASA registries, immortal seeds).
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import openpyxl
import pandas as pd

logger = logging.getLogger("talentops.sheet_seeder")

EXCEL_FILE_PATH = r"C:\Users\User\.gemini\antigravity\brain\285f6c8d-71ab-4abe-9e7b-e4d39e260a9f\.user_uploaded\media_1791206573787.xlsx"
STATE_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "sheet_harvest_state.json")


def clean_domain(val: Any) -> str:
    if not val or not isinstance(val, str):
        return ""
    val = val.lower().strip()
    val = re.sub(r'^https?://', '', val)
    val = re.sub(r'^www\.', '', val)
    val = val.split('/')[0].split('?')[0].split('#')[0].strip()
    if '.' in val and len(val) >= 4 and not val.endswith('.'):
        return val
    return ""


def clean_company_name(name: Any, domain: str = "") -> str:
    if not name or not isinstance(name, str):
        if domain:
            return domain.split('.')[0].replace('-', ' ').title()
        return ""
    name = str(name).strip()
    if name.lower() in ['nan', 'none', 'null', '']:
        if domain:
            return domain.split('.')[0].replace('-', ' ').title()
        return ""
    return name


class SheetTargetSeeder:
    """
    Stateful seeder that feeds companies into the harvester in strict sheet order:
    Ritik -> Anek -> Suhani -> Global
    """

    SHEET_ORDER = ["Ritik", "Anek", "Suhani"]

    def __init__(self, excel_path: str = EXCEL_FILE_PATH, state_path: str = STATE_FILE_PATH):
        self.excel_path = excel_path
        self.state_path = state_path
        self._catalog: Dict[str, List[Dict[str, Any]]] = {}
        self._state: Dict[str, Any] = {
            "current_sheet_index": 0,
            "harvested_domains": {},
            "sheet_progress": {"Ritik": 0, "Anek": 0, "Suhani": 0},
            "last_updated": None
        }
        self._load_state()
        self._load_catalog()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.warning("[SHEET SEEDER] Could not load state file, using fresh state: %s", e)

    def _save_state(self):
        try:
            self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning("[SHEET SEEDER] Could not persist state: %s", e)

    def _load_catalog(self):
        if not os.path.exists(self.excel_path):
            logger.warning("[SHEET SEEDER] Excel target file not found at %s", self.excel_path)
            return

        try:
            # 1. Ritik
            df_ritik = pd.read_excel(self.excel_path, sheet_name="Ritik")
            ritik_targets = []
            seen_ritik = set()
            for idx, row in df_ritik.iterrows():
                dom = clean_domain(str(row.get('Company / organization website', '')))
                cname = clean_company_name(row.get('Unnamed: 1', ''), dom)
                dflag = str(row.get('Filtered - Date wise', '')).strip()
                if dom and dom not in seen_ritik:
                    seen_ritik.add(dom)
                    ritik_targets.append({
                        "company_name": cname,
                        "domain": dom,
                        "sheet": "Ritik",
                        "date_flagged": 'yes' in dflag.lower(),
                        "recruiter_name": "",
                        "recruiter_email": "",
                        "row_index": idx + 2
                    })
            self._catalog["Ritik"] = ritik_targets

            # 2. Anek
            df_anek = pd.read_excel(self.excel_path, sheet_name="Anek")
            anek_targets = []
            seen_anek = set()
            for idx, row in df_anek.iterrows():
                dom = clean_domain(str(row.get('Website URL', '')))
                cname = clean_company_name(row.get('Company Name', ''), dom)
                dflag = str(row.get('Filtered - Date wise', '')).strip()
                rname = str(row.get('R- Name', '')).strip() if pd.notna(row.get('R- Name')) else ""
                remail = str(row.get('R-Email', '')).strip() if pd.notna(row.get('R-Email')) else ""
                if dom and dom not in seen_anek:
                    seen_anek.add(dom)
                    anek_targets.append({
                        "company_name": cname,
                        "domain": dom,
                        "sheet": "Anek",
                        "date_flagged": 'yes' in dflag.lower(),
                        "recruiter_name": rname if rname.lower() != 'nan' else "",
                        "recruiter_email": remail if remail.lower() != 'nan' else "",
                        "row_index": idx + 2
                    })
            self._catalog["Anek"] = anek_targets

            # 3. Suhani
            df_suhani = pd.read_excel(self.excel_path, sheet_name="Suhani")
            suhani_targets = []
            seen_suhani = set()
            for idx, row in df_suhani.iterrows():
                dom = clean_domain(str(row.get('URL', '')))
                cname = clean_company_name(row.get('Company Name', ''), dom)
                dflag = str(row.get('Filtered - Date wise', '')).strip()
                rname = str(row.get('R. Name', '')).strip() if pd.notna(row.get('R. Name')) else ""
                if dom and dom not in seen_suhani:
                    seen_suhani.add(dom)
                    suhani_targets.append({
                        "company_name": cname,
                        "domain": dom,
                        "sheet": "Suhani",
                        "date_flagged": 'yes' in dflag.lower(),
                        "recruiter_name": rname if rname.lower() != 'nan' else "",
                        "recruiter_email": "",
                        "row_index": idx + 2
                    })
            self._catalog["Suhani"] = suhani_targets

            logger.info(
                "[SHEET SEEDER] Loaded sheet catalog: Ritik (%d), Anek (%d), Suhani (%d)",
                len(ritik_targets), len(anek_targets), len(suhani_targets)
            )
        except Exception as e:
            logger.error("[SHEET SEEDER] Error loading catalog from Excel: %s", e)

    def get_catalog_stats(self) -> Dict[str, Any]:
        """Returns statistics of all target sheets and progress."""
        return {
            "sheets": {
                name: {
                    "total_companies": len(self._catalog.get(name, [])),
                    "harvested_count": sum(1 for t in self._catalog.get(name, []) if t["domain"] in self._state["harvested_domains"]),
                    "remaining_count": sum(1 for t in self._catalog.get(name, []) if t["domain"] not in self._state["harvested_domains"]),
                }
                for name in self.SHEET_ORDER
            },
            "current_active_sheet": self.get_current_active_sheet(),
            "all_sheets_completed": self.are_all_sheets_completed(),
            "total_harvested_domains": len(self._state["harvested_domains"])
        }

    def get_current_active_sheet(self) -> Optional[str]:
        """Returns the current sheet being processed (Ritik -> Anek -> Suhani)."""
        for sheet_name in self.SHEET_ORDER:
            targets = self._catalog.get(sheet_name, [])
            pending = [t for t in targets if t["domain"] not in self._state["harvested_domains"]]
            if pending:
                return sheet_name
        return None  # All sheets completed!

    def are_all_sheets_completed(self) -> bool:
        """Returns True if every company in Ritik, Anek, and Suhani has been harvested."""
        return self.get_current_active_sheet() is None

    def get_next_sheet_targets(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Pulls the next batch of targets adhering strictly to sheet order:
        Ritik -> Anek -> Suhani.
        Returns empty list when all 3 sheets are completed (releasing to global targets).
        """
        active_sheet = self.get_current_active_sheet()
        if not active_sheet:
            return []

        targets = self._catalog.get(active_sheet, [])
        # Prioritize flagged (date-wise = yes) within the active sheet first, then remaining
        pending = [t for t in targets if t["domain"] not in self._state["harvested_domains"]]
        pending_flagged = [t for t in pending if t.get("date_flagged")]
        pending_other = [t for t in pending if not t.get("date_flagged")]
        ordered_candidates = pending_flagged + pending_other

        selected = ordered_candidates[:limit]
        return [
            {
                "domain": t["domain"],
                "company_name": t["company_name"],
                "existing_contacts": 0,
                "priority": f"sheet_priority_{active_sheet.lower()}",
                "registry_tier": f"USER_SHEET_{active_sheet.upper()}",
                "sheet_source": active_sheet,
                "recruiter_hint": t.get("recruiter_name"),
                "email_hint": t.get("recruiter_email"),
            }
            for t in selected
        ]

    def mark_domain_harvested(self, domain: str, sheet: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Marks a domain as harvested in persistent state."""
        clean_d = clean_domain(domain)
        if not clean_d:
            return
        self._state["harvested_domains"][clean_d] = {
            "harvested_at": datetime.now(timezone.utc).isoformat(),
            "sheet": sheet,
            "details": details or {}
        }
        if sheet and sheet in self._state["sheet_progress"]:
            self._state["sheet_progress"][sheet] = self._state["sheet_progress"].get(sheet, 0) + 1
        self._save_state()

    def get_sheet_targets_list(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Returns the full list of targets for a specific sheet."""
        return self._catalog.get(sheet_name, [])


sheet_target_seeder = SheetTargetSeeder()
