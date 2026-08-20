"""
Data Harvester Service: Universal multi-format raw data discovery & ingestion.
Supports Excel (.xlsx, .xls), CSV (.csv), SQLite (.db, .sqlite), Parquet (.parquet),
and unstructured text dumps (.txt).
"""
import os
import re
import sys
import glob
import logging
import sqlite3
from typing import List, Dict, Any, Generator, Optional
import pandas as pd
import duckdb

logger = logging.getLogger("data_harvester")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Canonical Schema & Field Aliases ──────────────────────────────────────────
COLUMN_ALIASES = {
    "recruiter_name": [
        "recruiter_name", "name", "full_name", "contact_name", "recruiter",
        "person_name", "candidate_name", "employee_name", "contact person",
        "full name", "recruiter name", "contact", "person", "full_names",
        "people", "name of recruiter", "talent_partner", "recruiter_full_name"
    ],
    "first_name": ["first_name", "firstname", "fname", "first name", "first"],
    "last_name": ["last_name", "lastname", "lname", "last name", "last"],
    "email": [
        "email", "email_address", "mail", "work_email", "primary_email",
        "e-mail", "recruiter_email", "email id", "mail id", "contact_email",
        "emailaddress", "email_1", "email1", "primary email", "work email",
        "corporate_email", "direct_email"
    ],
    "email2": ["email2", "alternate_email", "alt_email", "secondary_email", "email_2", "personal_email", "alt email"],
    "email3": ["email3", "email_3"],
    "email4": ["email4", "email_4"],
    "phone": [
        "phone", "phone_number", "mobile", "cell", "telephone", "tel",
        "direct_phone", "contact_number", "phone number", "direct number",
        "work_phone", "office_phone", "mobile_phone", "contact_phone", "phone_1", "phone1",
        "primary phone", "cell phone"
    ],
    "phone2": ["phone2", "alt_phone", "alternate_phone", "secondary_phone", "phone_2", "mobile2", "alt phone"],
    "phone3": ["phone3", "phone_3"],
    "phone4": ["phone4", "phone_4"],
    "company_id": [
        "company_id", "company", "company_name", "firm", "organization",
        "agency", "client", "employer", "company name", "staffing_firm",
        "business_name", "current_company", "account_name"
    ],
    "title": [
        "title", "job_title", "designation", "position", "role", "job title",
        "current_title", "headline", "job", "recruiter_title", "professional_title"
    ],
    "location": [
        "location", "city_state", "address", "full_location", "geographic_location",
        "office_location", "work_location", "geo"
    ],
    "state": [
        "state", "state_code", "us_state", "region", "province", "st", "state_abbr",
        "work_state", "candidate_state"
    ],
    "normalized_city": ["city", "normalized_city", "metro_city", "town", "work_city"],
    "linkedin": [
        "linkedin", "linkedin_url", "linkedin_profile", "profile_url", "social_url",
        "li_url", "linkedin link", "linkedin_link", "public_profile_url", "linkedin_handle"
    ],
    "specialization": [
        "specialization", "industry", "domain", "focus_area", "recruiting_domain",
        "niche", "vertical", "skills", "discipline"
    ],
    "notes": ["notes", "comments", "description", "remarks", "about", "summary", "additional_info"]
}


def fuzzy_match_columns(df_columns: List[str]) -> Dict[str, str]:
    """
    Given raw dataframe column names, maps them to canonical schema fields.
    Returns dict: { raw_col_name: canonical_field }
    """
    mapping = {}
    normalized_cols = {re.sub(r"[_\s\-\.\/]+", " ", str(c)).strip().lower(): c for c in df_columns}

    for canonical_field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_norm = re.sub(r"[_\s\-\.\/]+", " ", alias).strip().lower()
            for col_norm, original_col in normalized_cols.items():
                if original_col in mapping:
                    continue
                if col_norm == alias_norm or col_norm == alias_norm.replace(" ", ""):
                    mapping[original_col] = canonical_field
                    break
    return mapping


class DataHarvester:
    """Discovers and harvests raw recruiter/talent records from local directories."""

    def __init__(self):
        self.stats = {
            "files_scanned": 0,
            "records_extracted": 0,
            "errors": 0
        }

    def scan_directories(self, search_paths: List[str]) -> List[str]:
        """Finds all candidate files across given directories with fast directory pruning."""
        discovered_files = []
        extensions = {".xlsx", ".xls", ".csv", ".parquet", ".db", ".sqlite", ".txt", ".json"}
        exclude_dirs = {
            "node_modules", ".git", ".pytest_cache", ".venv", "venv", "appdata", 
            "site-packages", "system_generated", "$recycle.bin", "system volume information",
            "windows", "program files", "program files (x86)", ".vscode", ".cache", ".npm"
        }
        keywords = [
            "recruiter", "talent", "candidate", "company", "people",
            "contact", "lead", "email", "job", "staffing", "clean",
            "master", "extract", "sheet", "export", "roster", "saurabh",
            "abhishek", "praveen", "yatin", "inbox", "data", "tek", "number"
        ]

        for path in search_paths:
            if not os.path.exists(path):
                continue
            if os.path.isfile(path):
                discovered_files.append(path)
                continue

            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs and not d.startswith('.')]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in extensions and not f.startswith("~$") and not f.startswith("."):
                        fpath = os.path.join(root, f)
                        try:
                            sz = os.path.getsize(fpath)
                            if sz < 100:
                                continue
                            fname = f.lower()
                            if any(k in fname for k in keywords) or sz > 50_000:
                                discovered_files.append(fpath)
                        except Exception:
                            pass

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in discovered_files:
            abs_f = os.path.abspath(f)
            if abs_f not in seen:
                seen.add(abs_f)
                unique_files.append(abs_f)
        return unique_files

    def harvest_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Harvests records from a single file depending on extension."""
        ext = os.path.splitext(file_path)[1].lower()
        records = []
        try:
            if ext in [".xlsx", ".xls"]:
                records = self._harvest_excel(file_path)
            elif ext == ".csv":
                records = self._harvest_csv(file_path)
            elif ext in [".db", ".sqlite"]:
                records = self._harvest_sqlite(file_path)
            elif ext == ".parquet":
                records = self._harvest_parquet(file_path)
            elif ext == ".txt":
                records = self._harvest_txt(file_path)
            elif ext == ".json":
                records = self._harvest_json(file_path)
            
            self.stats["files_scanned"] += 1
            self.stats["records_extracted"] += len(records)
            logger.info(f"Harvested {len(records):,} records from {os.path.basename(file_path)}")
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Failed to harvest {file_path}: {e}")
        return records

    def _harvest_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Extracts records from JSON files (list of dicts, or dict with keys containing list)."""
        import json
        records = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                    if len(df.columns) > 15:
                        logger.info(f"Skipping JSON {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15)")
                        return []
                    return self._standardize_dataframe(df, os.path.basename(file_path))
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        df = pd.DataFrame(v)
                        if len(df.columns) > 15:
                            logger.info(f"Skipping JSON {os.path.basename(file_path)}::{k}: has {len(df.columns)} columns (> 15)")
                            continue
                        sheet_recs = self._standardize_dataframe(df, f"{os.path.basename(file_path)}::{k}")
                        records.extend(sheet_recs)
        except Exception as e:
            logger.debug(f"JSON read error on {file_path}: {e}")
        return records

    def _harvest_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads all sheets in an Excel workbook, enforcing <= 15 column rule."""
        records = []
        try:
            try:
                excel_file = pd.ExcelFile(file_path, engine="calamine")
            except Exception:
                excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    if df.empty or len(df.columns) < 2:
                        continue
                    if len(df.columns) > 15:
                        logger.info(f"Skipping sheet '{sheet_name}' in {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15 max)")
                        continue
                    sheet_records = self._standardize_dataframe(df, f"{os.path.basename(file_path)}::{sheet_name}")
                    records.extend(sheet_records)
                except Exception as sheet_err:
                    logger.debug(f"Sheet {sheet_name} error in {file_path}: {sheet_err}")
        except Exception as e:
            logger.debug(f"Excel read error on {file_path}: {e}")
        return records

    def _harvest_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads CSV with encoding fallbacks and <= 15 column rule."""
        for enc in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                df = pd.read_csv(file_path, encoding=enc, low_memory=False, on_bad_lines="skip")
                if not df.empty:
                    if len(df.columns) > 15:
                        logger.info(f"Skipping CSV {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15 max)")
                        return []
                    return self._standardize_dataframe(df, os.path.basename(file_path))
            except Exception:
                continue
        return []

    def _harvest_sqlite(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads SQLite tables matching candidate/recruiter entities with <= 15 columns."""
        records = []
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            for t in tables:
                tname = t[0]
                if tname.startswith("sqlite_") or tname in ["roles", "permissions", "role_permissions", "users", "sessions", "login_history", "trusted_devices"]:
                    continue
                try:
                    df = pd.read_sql_query(f"SELECT * FROM `{tname}`", conn)
                    if not df.empty:
                        if len(df.columns) > 15:
                            logger.info(f"Skipping SQLite table {tname} in {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15 max)")
                            continue
                        recs = self._standardize_dataframe(df, f"{os.path.basename(file_path)}::{tname}")
                        records.extend(recs)
                except Exception as tbl_err:
                    logger.debug(f"SQLite table {tname} error in {file_path}: {tbl_err}")
            conn.close()
        except Exception as e:
            logger.debug(f"SQLite error on {file_path}: {e}")
        return records

    def _harvest_parquet(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads Parquet file via DuckDB zero-copy or pandas with <= 15 columns."""
        try:
            con = duckdb.connect()
            df = con.execute(f"SELECT * FROM '{file_path}'").df()
            if not df.empty:
                if len(df.columns) > 15:
                    logger.info(f"Skipping Parquet {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15 max)")
                    return []
                return self._standardize_dataframe(df, os.path.basename(file_path))
        except Exception as e:
            try:
                df = pd.read_parquet(file_path)
                if not df.empty:
                    if len(df.columns) > 15:
                        logger.info(f"Skipping Parquet {os.path.basename(file_path)}: has {len(df.columns)} columns (> 15 max)")
                        return []
                    return self._standardize_dataframe(df, os.path.basename(file_path))
            except Exception as pe:
                logger.debug(f"Parquet error on {file_path}: {pe}")
        return []

    def _harvest_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """Extracts structured contact blocks from unstructured text dumps (e.g. TEKsystems_html.txt)."""
        records = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract email addresses and nearby context
            email_pattern = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
            phone_pattern = re.compile(r"(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})")
            
            emails = set(email_pattern.findall(content))
            for em in emails:
                if any(bad in em.lower() for bad in ["example.com", "test@", "schema.org", "sentry.io", ".png", ".jpg", ".svg", "noreply", "support@"]):
                    continue
                # Extract surrounding snippet (150 chars before and after)
                idx = content.find(em)
                snippet = content[max(0, idx - 150): min(len(content), idx + len(em) + 150)]
                
                # Look for phone in snippet
                phone_match = phone_pattern.search(snippet)
                phone_val = f"{phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}" if phone_match else None
                
                # Derive company from domain
                domain = em.split("@")[-1].lower()
                company_name = domain.split(".")[0].title()
                
                # Infer name from email username if firstname.lastname
                user_part = em.split("@")[0]
                name_val = None
                if "." in user_part:
                    name_parts = user_part.split(".")
                    if len(name_parts) == 2 and all(p.isalpha() for p in name_parts):
                        name_val = f"{name_parts[0].title()} {name_parts[1].title()}"

                records.append({
                    "email": em.lower().strip(),
                    "phone": phone_val,
                    "recruiter_name": name_val,
                    "company_id": company_name,
                    "data_source": f"text_dump::{os.path.basename(file_path)}"
                })
        except Exception as e:
            logger.debug(f"Text dump parsing error on {file_path}: {e}")
        return records

    def _standardize_dataframe(self, df: pd.DataFrame, source_tag: str) -> List[Dict[str, Any]]:
        """Fast vectorized column mapping and record conversion with strict <= 15 column rule."""
        if len(df.columns) > 15:
            logger.info(f"Skipping {source_tag}: has {len(df.columns)} columns (> 15 column limit)")
            return []

        col_map = fuzzy_match_columns(list(df.columns))
        target_fields = set(col_map.values())
        if not ("email" in target_fields or "recruiter_name" in target_fields or "first_name" in target_fields or "phone" in target_fields):
            return []

        # Rename recognized columns
        df_renamed = df.rename(columns=col_map)
        
        # Keep only canonical columns
        valid_cols = [c for c in set(col_map.values()) if c in df_renamed.columns]
        if not valid_cols:
            return []
        
        # Handle duplicate columns if any
        df_sub = df_renamed.loc[:, ~df_renamed.columns.duplicated()][valid_cols].copy()
        
        # Merge first_name and last_name if recruiter_name missing
        if "recruiter_name" not in df_sub.columns and "first_name" in df_sub.columns:
            if "last_name" in df_sub.columns:
                df_sub["recruiter_name"] = (df_sub["first_name"].fillna("").astype(str).str.strip() + " " + df_sub["last_name"].fillna("").astype(str).str.strip()).str.strip()
            else:
                df_sub["recruiter_name"] = df_sub["first_name"].fillna("").astype(str).str.strip()
                
        df_sub["data_source"] = source_tag
        
        # Filter rows that have at least email or (recruiter_name and (phone or company_id))
        cond = False
        if "email" in df_sub.columns:
            cond = cond | (df_sub["email"].notna() & (df_sub["email"].astype(str).str.strip() != ""))
        if "recruiter_name" in df_sub.columns:
            has_name = df_sub["recruiter_name"].notna() & (df_sub["recruiter_name"].astype(str).str.strip() != "")
            has_contact = False
            if "phone" in df_sub.columns:
                has_contact = has_contact | (df_sub["phone"].notna() & (df_sub["phone"].astype(str).str.strip() != ""))
            if "company_id" in df_sub.columns:
                has_contact = has_contact | (df_sub["company_id"].notna() & (df_sub["company_id"].astype(str).str.strip() != ""))
            cond = cond | (has_name & has_contact)

        if isinstance(cond, pd.Series):
            df_filtered = df_sub[cond]
        else:
            df_filtered = df_sub

        return df_filtered.to_dict(orient="records")
