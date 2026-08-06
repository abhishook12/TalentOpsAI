"""
RecruiterStore: Unified query engine using DuckDB over Parquet files.
Provides search, filter, pagination, and count methods that mirror
the existing SQLAlchemy-based queries but read from compressed Parquet.

The site sees ONE unified dataset regardless of storage backend.
"""
import os
import logging
import threading
import time
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger("recruiter_store")

# Use an absolute path relative to this file's location to ensure it works on both Windows and Linux (Render)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PARQUET_DIR = os.environ.get("PARQUET_DIR", os.path.join(BASE_DIR, "data"))
PARQUET_FILE = os.path.join(PARQUET_DIR, "recruiters_full.parquet")

# Lazy import duckdb — only when needed
_duckdb = None
def _get_duckdb():
    global _duckdb
    if _duckdb is None:
        import duckdb
        _duckdb = duckdb
    return _duckdb


class RecruiterStore:
    """
    In-memory DuckDB-backed query engine for recruiter data stored in Parquet.
    Falls back to PostgreSQL if Parquet is unavailable.
    """

    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._loaded = False
        self._record_count = 0
        self._last_load_time = None

    def _ensure_loaded(self):
        """Load Parquet into DuckDB if not already loaded, or if file changed."""
        current_mtime = 0
        try:
            current_mtime = os.path.getmtime(PARQUET_FILE)
        except OSError:
            pass
            
        if self._loaded and self._conn is not None and getattr(self, '_last_mtime', -1) == current_mtime:
            return
            
        with self._lock:
            try:
                current_mtime = os.path.getmtime(PARQUET_FILE)
            except OSError:
                current_mtime = 0
                
            if self._loaded and self._conn is not None and getattr(self, '_last_mtime', -1) == current_mtime:
                return
                
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
                
            self._load()
            self._last_mtime = current_mtime

    def _download_from_storage(self):
        """Download the Parquet file from Supabase Storage if it doesn't exist locally or if size differs."""
        import urllib.request
        import shutil
        import time
        
        url = f"https://dcqvsvgrdsrgnbwwssup.supabase.co/storage/v1/object/public/data-assets/recruiters_full.parquet?v={int(time.time())}"
        
        try:
            # Check remote size using a HEAD request (or just open and check length)
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as response:
                remote_size = int(response.headers.get('Content-Length', 0))
                
            if os.path.exists(PARQUET_FILE):
                local_size = os.path.getsize(PARQUET_FILE)
                if local_size == remote_size and remote_size > 0:
                    logger.info(f"Local Parquet file matches remote size ({local_size} bytes). Skipping download.")
                    return
                else:
                    logger.info(f"Local size ({local_size}) differs from remote ({remote_size}). Re-downloading...")
        except Exception as e:
            logger.warning(f"Failed to check remote Parquet size: {e}. Will rely on local existence.")
            if os.path.exists(PARQUET_FILE):
                return
            
        logger.info(f"Downloading Parquet from Supabase Storage to {PARQUET_FILE}...")
        try:
            os.makedirs(os.path.dirname(PARQUET_FILE), exist_ok=True)
            with urllib.request.urlopen(url, timeout=60) as response, open(PARQUET_FILE, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            logger.info(f"Successfully downloaded Parquet file ({os.path.getsize(PARQUET_FILE) / (1024*1024):.2f} MB)")
        except Exception as e:
            logger.error(f"Failed to download Parquet from Supabase: {e}")

    def _load(self):
        """Load the Parquet file into DuckDB."""
        duckdb = _get_duckdb()
        
        self._download_from_storage()
        
        if not os.path.exists(PARQUET_FILE):
            logger.warning(f"Parquet file not found: {PARQUET_FILE}. RecruiterStore will be empty.")
            self._conn = duckdb.connect(":memory:")
            self._loaded = True
            return

        start = time.time()
        self._conn = duckdb.connect(":memory:")
        
        # Create a view over the Parquet file (memory-efficient, reads on demand)
        self._conn.execute(f"""
            CREATE VIEW recruiters AS 
            SELECT * FROM read_parquet('{PARQUET_FILE.replace(os.sep, '/')}')
        """)
        
        self._record_count = self._conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
        elapsed = time.time() - start
        
        logger.info(f"RecruiterStore loaded {self._record_count:,} recruiters from Parquet in {elapsed:.2f}s")
        self._loaded = True
        self._last_load_time = time.time()

    def reload(self):
        """Force reload from Parquet (e.g. after sync)."""
        with self._lock:
            if self._conn:
                self._conn.close()
            self._conn = None
            self._loaded = False
        self._ensure_loaded()

    @property
    def total_count(self) -> int:
        self._ensure_loaded()
        return self._record_count

    # ─── Core Query Methods ───

    def _df_to_dict(self, df):
        if df.empty:
            return []
        import math
        import pandas as pd
        
        results = df.to_dict(orient='records')
        clean_results = []
        for row in results:
            clean_row = {}
            for k, v in row.items():
                if v is None:
                    clean_row[k] = None
                elif isinstance(v, float) and math.isnan(v):
                    clean_row[k] = None
                elif pd.isna(v):
                    clean_row[k] = None
                else:
                    clean_row[k] = v
            clean_results.append(clean_row)
        return clean_results

    def get_by_id(self, recruiter_id: int) -> Optional[Dict[str, Any]]:
        """Get a single recruiter by ID."""
        self._ensure_loaded()
        result = self._conn.execute(
            "SELECT * FROM recruiters WHERE recruiter_id = ?", [recruiter_id]
        ).fetchdf()
        if result.empty:
            return None
        return self._df_to_dict(result)[0]

    def list_recruiters(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        state: Optional[str] = None,
        company_id: Optional[int] = None,
        company_name: Optional[str] = None,
        specialization: Optional[str] = None,
        has_phone: Optional[bool] = None,
        is_active: Optional[bool] = None,
        needs_review: Optional[bool] = None,
        email_status: Optional[str] = None,
        data_source: Optional[str] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List recruiters with filtering and pagination.
        Returns (results, total_count).
        """
        self._ensure_loaded()

        where_clauses = []
        params = []

        if search:
            search_lower = search.lower()
            where_clauses.append("""(
                LOWER(COALESCE(recruiter_name, '')) LIKE ? 
                OR LOWER(COALESCE(email, '')) LIKE ?
                OR LOWER(COALESCE(specialization, '')) LIKE ?
                OR CAST(COALESCE(company_id, 0) AS VARCHAR) IN (
                    SELECT CAST(company_id AS VARCHAR) FROM recruiters 
                    WHERE LOWER(COALESCE(recruiter_name, '')) LIKE ? LIMIT 1
                )
            )""")
            like_pat = f"%{search_lower}%"
            params.extend([like_pat, like_pat, like_pat, like_pat])

        if state:
            where_clauses.append("UPPER(COALESCE(state, '')) = ?")
            params.append(state.upper())

        if company_id is not None:
            where_clauses.append("company_id = ?")
            params.append(company_id)

        if specialization:
            where_clauses.append("LOWER(COALESCE(specialization, '')) LIKE ?")
            params.append(f"%{specialization.lower()}%")

        if has_phone is True:
            where_clauses.append("phone IS NOT NULL AND phone != ''")
        elif has_phone is False:
            where_clauses.append("(phone IS NULL OR phone = '')")

        if is_active is not None:
            where_clauses.append("is_active = ?")
            params.append(is_active)

        if needs_review is not None:
            where_clauses.append("needs_review = ?")
            params.append(needs_review)

        if email_status:
            where_clauses.append("email_status = ?")
            params.append(email_status)

        if data_source:
            where_clauses.append("data_source = ?")
            params.append(data_source)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Count
        count_sql = f"SELECT COUNT(*) FROM recruiters WHERE {where_sql}"
        total_count = self._conn.execute(count_sql, params).fetchone()[0]

        # Sort
        valid_sorts = {
            "created_at": "created_at",
            "name": "recruiter_name",
            "company": "company_id",
            "state": "state",
            "completeness": "completeness_score",
            "last_scan_at": "last_scan_at",
        }
        sort_col = valid_sorts.get(sort_by, "created_at")
        sort_dir = "DESC" if sort_desc else "ASC"

        offset = (page - 1) * limit
        query_sql = f"""
            SELECT * FROM recruiters 
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir} NULLS LAST
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        df = self._conn.execute(query_sql, params).fetchdf()
        results = self._df_to_dict(df)

        return results, total_count

    def search(
        self,
        q: str,
        company: Optional[str] = None,
        location: Optional[str] = None,
        specialization: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Smart search across recruiter name, email, company, specialization.
        Returns ranked results.
        """
        self._ensure_loaded()
        q_lower = q.lower()
        q_like = f"%{q_lower}%"

        where_parts = ["""(
            LOWER(COALESCE(recruiter_name, '')) LIKE ?
            OR LOWER(COALESCE(email, '')) LIKE ?
            OR LOWER(COALESCE(email2, '')) LIKE ?
            OR LOWER(COALESCE(email3, '')) LIKE ?
            OR LOWER(COALESCE(email4, '')) LIKE ?
            OR LOWER(COALESCE(CAST(alternate_emails AS VARCHAR), '')) LIKE ?
            OR LOWER(COALESCE(phone, '')) LIKE ?
            OR LOWER(COALESCE(phone2, '')) LIKE ?
            OR LOWER(COALESCE(specialization, '')) LIKE ?
        )"""]
        params = [q_like] * 9

        if company:
            where_parts.append("company_id IN (SELECT company_id FROM recruiters WHERE LOWER(COALESCE(recruiter_name,'')) LIKE ? LIMIT 100)")
            params.append(f"%{company.lower()}%")

        if location:
            where_parts.append("UPPER(COALESCE(state, '')) = ?")
            params.append(location.upper()[:2])

        if specialization:
            where_parts.append("LOWER(COALESCE(specialization, '')) LIKE ?")
            params.append(f"%{specialization.lower()}%")

        where_sql = " AND ".join(where_parts)

        # Score-based ranking
        sql = f"""
            SELECT *,
                (CASE WHEN LOWER(COALESCE(recruiter_name,'')) = ? THEN 200
                      WHEN LOWER(COALESCE(recruiter_name,'')) LIKE ? || '%' THEN 130
                      WHEN LOWER(COALESCE(recruiter_name,'')) LIKE ? THEN 100
                      ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(email,'')) = ? THEN 200
                        WHEN LOWER(COALESCE(email,'')) LIKE ? THEN 80
                        ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(specialization,'')) LIKE ? THEN 40
                        ELSE 0 END
                 + COALESCE(completeness_score, 0) / 4
                ) AS relevance_score
            FROM recruiters
            WHERE {where_sql}
            ORDER BY relevance_score DESC, completeness_score DESC NULLS LAST
            LIMIT ?
        """
        score_params = [q_lower, q_lower, q_like, q_lower, q_like, q_like]
        all_params = score_params + params + [limit]

        df = self._conn.execute(sql, all_params).fetchdf()
        return self._df_to_dict(df)

    def count_by_company(self, company_id: int) -> int:
        """Count recruiters for a given company."""
        self._ensure_loaded()
        result = self._conn.execute(
            "SELECT COUNT(*) FROM recruiters WHERE company_id = ?", [company_id]
        ).fetchone()
        return result[0] if result else 0

    def company_recruiter_counts(self) -> Dict[int, int]:
        """Get recruiter counts for all companies."""
        self._ensure_loaded()
        df = self._conn.execute("""
            SELECT company_id, COUNT(*) as cnt 
            FROM recruiters 
            WHERE company_id IS NOT NULL
            GROUP BY company_id
        """).fetchdf()
        return dict(zip(df['company_id'].tolist(), df['cnt'].tolist()))

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        self._ensure_loaded()
        stats = {
            "total_recruiters": self._record_count,
            "loaded": self._loaded,
            "last_load_time": self._last_load_time,
            "parquet_file": PARQUET_FILE,
            "parquet_exists": os.path.exists(PARQUET_FILE),
        }
        if self._loaded and self._conn:
            stats["with_company"] = self._conn.execute(
                "SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL"
            ).fetchone()[0]
            stats["with_phone"] = self._conn.execute(
                "SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL AND phone != ''"
            ).fetchone()[0]
            stats["email_status_breakdown"] = dict(
                self._conn.execute(
                    "SELECT COALESCE(email_status, 'unknown'), COUNT(*) FROM recruiters GROUP BY email_status"
                ).fetchall()
            )
        return stats


# Singleton instance
recruiter_store = RecruiterStore()
