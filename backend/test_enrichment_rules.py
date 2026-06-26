import unittest
from enrich_recruiter_contacts import EnrichmentWorker
from app.models.models import Recruiter, Company
from unittest.mock import MagicMock

class DummyArgs:
    apply = False
    dry_run = True
    minimum_confidence = 70
    run_id = "test"
    batch_size = 100

class TestEnrichmentRules(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.worker = EnrichmentWorker(self.db, DummyArgs())

    def test_is_human_name(self):
        # Good names
        self.assertTrue(self.worker.is_human_name("Joe Phillips"))
        self.assertTrue(self.worker.is_human_name("Mackenzie Harris"))

        # Bad role-based names
        self.assertFalse(self.worker.is_human_name("Insight Global"))
        self.assertFalse(self.worker.is_human_name("Left Vm"))
        self.assertFalse(self.worker.is_human_name("System Pros"))
        self.assertFalse(self.worker.is_human_name("Soal Tech"))
        self.assertFalse(self.worker.is_human_name("Synergy Interactive"))
        self.assertFalse(self.worker.is_human_name("Peer Technical"))

        # Bad Initials
        self.assertFalse(self.worker.is_human_name("J. Smith"))
        self.assertFalse(self.worker.is_human_name("J Smith"))
        self.assertFalse(self.worker.is_human_name("Brooke S"))

    def test_never_overwrite_non_empty(self):
        r = Recruiter(recruiter_id=1, email="tatum.teer@thehtgroup.com", recruiter_name="Joe Phillips")
        r.company = Company(company_id=1, website="thehtgroup.com", email_pattern="first.last")
        
        # Mock pattern detection
        self.worker.detect_company_patterns = MagicMock(return_value={"domain": "thehtgroup.com", "pattern": "first.last", "confidence": 90})
        
        outcome = self.worker.process_recruiter(r)
        self.assertEqual(outcome, "SKIPPED_ALREADY_ENRICHED")

    def test_reject_role_based_local_part(self):
        r = Recruiter(recruiter_id=2, email=None, recruiter_name="I Global")
        r.company = Company(company_id=2, website="medasource.com", email_pattern="first")
        
        # Even if name somehow passed, local part rejection
        self.worker.detect_company_patterns = MagicMock(return_value={"domain": "medasource.com", "pattern": "first", "confidence": 90})
        
        # Override is_human_name to pretend it passed, to test the secondary check
        self.worker.is_human_name = MagicMock(return_value=True)
        
        from unittest.mock import patch
        with patch('enrich_recruiter_contacts.generate_email', return_value="iglobal@medasource.com"):
            outcome = self.worker.process_recruiter(r)
            self.assertEqual(outcome, "REJECTED_LOW_CONFIDENCE")
            
            outcome = self.worker.process_recruiter(r)
            self.assertEqual(outcome, "REJECTED_LOW_CONFIDENCE")

    def test_confidence_threshold(self):
        r = Recruiter(recruiter_id=3, email=None, recruiter_name="Joe Phillips")
        r.company = Company(company_id=3, website="thehtgroup.com", email_pattern="first.last")
        
        self.worker.detect_company_patterns = MagicMock(return_value={"domain": "thehtgroup.com", "pattern": "first.last", "confidence": 70})
        self.worker._save_proposal = MagicMock()
        
        outcome = self.worker.process_recruiter(r)
        self.assertEqual(outcome, "PENDING_UPDATE")

    def test_suspicious_email_pending_update(self):
        r = Recruiter(recruiter_id=4, email="admin@thehtgroup.com", recruiter_name="Joe Phillips")
        r.company = Company(company_id=4, website="thehtgroup.com", email_pattern="first.last")
        
        self.worker.detect_company_patterns = MagicMock(return_value={"domain": "thehtgroup.com", "pattern": "first.last", "confidence": 90})
        self.worker._save_proposal = MagicMock()
        
        outcome = self.worker.process_recruiter(r)
        self.assertEqual(outcome, "PENDING_UPDATE")

    def test_concatenated_name_recovery(self):
        r = Recruiter(recruiter_id=5, email="joe.phillips@thehtgroup.com", recruiter_name="Joephillips")
        r.company = Company(company_id=5, website="thehtgroup.com", email_pattern="first.last")
        
        self.worker.detect_company_patterns = MagicMock(return_value={"domain": "thehtgroup.com", "pattern": "first.last", "confidence": 90})
        
        outcome = self.worker.process_recruiter(r)
        self.assertEqual(outcome, "SKIPPED_ALREADY_ENRICHED")

if __name__ == '__main__':
    unittest.main()
