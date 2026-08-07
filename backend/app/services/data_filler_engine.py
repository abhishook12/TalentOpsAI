import os
import time
import logging
import threading
from typing import List, Dict, Any

from app.services.recruiter_store import recruiter_store
from app.services.parquet_writer import parquet_writer

logger = logging.getLogger(__name__)

class DataFillerEngine:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self.batch_size = 5000
        self.cooldown_seconds = 2.0
        self.idle_seconds = 300.0
        self.is_running = False

        self.spec_keywords = [
            ('Information Technology', ['software', 'developer', 'engineer', 'devops', 'cloud', 'data', 'cyber', 'sap', 'java', 'python', '.net', 'frontend', 'backend', 'full stack', 'fullstack', 'tech', 'infrastructure', 'network', 'systems', 'database', 'ai ', 'machine learning', 'security', 'helpdesk', 'desktop support', 'qa', 'quality assurance', 'scrum', 'agile', 'product manager', 'ux', 'ui']),
            ('Healthcare', ['healthcare', 'medical', 'nurse', 'nursing', 'clinical', 'pharma', 'biotech', 'health ', 'dental', 'physician', 'therapist', 'hospital', 'patient']),
            ('Finance & Accounting', ['finance', 'financial', 'accounting', 'accountant', 'cpa', 'audit', 'tax', 'banking', 'investment', 'mortgage', 'loan', 'treasury', 'controller']),
            ('Engineering', ['mechanical', 'electrical', 'civil', 'structural', 'manufacturing', 'industrial', 'chemical engineer', 'aerospace']),
            ('Sales & Marketing', ['sales', 'marketing', 'business development', 'account executive', 'sdr', 'bdr', 'demand gen', 'brand', 'advertising', 'digital marketing', 'seo', 'content']),
            ('Human Resources', ['human resources', 'hr', 'talent', 'recruiting', 'recruiter', 'staffing', 'workforce', 'people operations', 'compensation', 'benefits', 'payroll', 'hris']),
            ('Legal', ['legal', 'attorney', 'lawyer', 'paralegal', 'compliance', 'regulatory', 'counsel', 'litigation']),
            ('Operations & Logistics', ['operations', 'logistics', 'supply chain', 'warehouse', 'procurement', 'transportation', 'fleet', 'distribution', 'inventory']),
            ('Construction & Trades', ['construction', 'plumber', 'electrician', 'hvac', 'carpenter', 'welder', 'mason', 'roofing']),
            ('Creative & Design', ['design', 'graphic', 'creative', 'photographer', 'video', 'animation', 'art director', 'copywriter']),
            ('Education', ['education', 'teacher', 'professor', 'instructor', 'training', 'curriculum', 'academic', 'tutor']),
            ('Executive', ['executive', 'ceo', 'cfo', 'cto', 'coo', 'cio', 'vp', 'vice president', 'director', 'chief', 'svp', 'evp', 'managing director', 'partner', 'principal']),
            ('Customer Service', ['customer service', 'customer support', 'call center', 'client services', 'support specialist']),
            ('Project Management', ['project manager', 'program manager', 'pmo', 'project coordinator', 'scrum master']),
            ('Administrative', ['administrative', 'office manager', 'executive assistant', 'receptionist', 'coordinator', 'clerk'])
        ]

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("DataFillerEngine is already running.")
            return

        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._run, name="DataFillerEngine", daemon=True)
        self._thread.start()
        logger.info("DataFillerEngine started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self.is_running = False
        logger.info("DataFillerEngine stopped.")

    def _infer_specialization(self, title: str) -> str:
        if not title:
            return None
        title_lower = title.lower()
        for category, keywords in self.spec_keywords:
            if any(kw in title_lower for kw in keywords):
                return category
        return 'General Staffing'

    def _run(self):
        logger.info("DataFillerEngine loop started.")
        while not self._stop_event.is_set():
            try:
                recruiter_store._ensure_loaded()
                conn = recruiter_store._conn

                # We fetch records where specialization is missing and title exists.
                # Phone numbers are intentionally skipped to prioritize accuracy.
                # to prioritize accuracy over aggressive filling.
                query = """
                SELECT recruiter_id, title
                FROM recruiters
                WHERE (specialization IS NULL OR specialization = '' OR LOWER(specialization) IN ('null', 'n/a', 'none', 'unknown'))
                  AND title IS NOT NULL AND title != ''
                LIMIT ? OFFSET ?
                """

                df = conn.execute(query, [self.batch_size, 0]).df()

                if df.empty:
                    logger.info("DataFillerEngine is idle; no missing specializations found.")
                    self._stop_event.wait(self.idle_seconds)
                    continue

                updates = []
                for _, row in df.iterrows():
                    spec = self._infer_specialization(row['title'])
                    if spec:
                        updates.append({
                            'recruiter_id': row['recruiter_id'],
                            'specialization': spec
                        })

                if updates:
                    updated_count = parquet_writer.update_records(updates)
                    logger.info(f"DataFillerEngine: Batch updated {updated_count} specializations.")
                else:
                    # Every matching row should be classifiable, but avoid a hot loop
                    # if malformed source data produces no usable update.
                    self._stop_event.wait(self.idle_seconds)
                    continue

                self._stop_event.wait(self.cooldown_seconds)

            except Exception as e:
                logger.error(f"DataFillerEngine Error: {e}")
                self._stop_event.wait(10) # Backoff on error

        self.is_running = False
        logger.info("DataFillerEngine stopped.")

data_filler_engine = DataFillerEngine()
