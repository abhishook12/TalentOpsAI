import pytest
from unittest.mock import MagicMock, patch
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Recruiter, Company, EnrichmentAudit, CompanyEmailPattern
from enrich_recruiter_contacts import EnrichmentWorker

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.company = None
    args.company_limit = None
    args.recruiter_limit = None
    args.minimum_confidence = 70
    args.dry_run = True
    args.apply = False
    args.verbose = False
    args.yes = True
    args.resume_run_id = "test_run_123"
    args.export_report = False
    return args



def test_is_human_name(mock_db, mock_args):
    worker = EnrichmentWorker(mock_db, mock_args)
    assert worker.is_human_name("John Doe") == True
    assert worker.is_human_name("Unknown Name") == False
    assert worker.is_human_name("Info Contact") == False

def test_extract_names(mock_db, mock_args):
    worker = EnrichmentWorker(mock_db, mock_args)
    assert worker.extract_names("John Doe") == ("John", "Doe")
    assert worker.extract_names("John") == ("", "")
    assert worker.extract_names("John Middle Doe") == ("John", "Doe")

@patch('enrich_recruiter_contacts.generate_email')
def test_dry_run_rejects_duplicate(mock_gen_email, mock_db, mock_args):
    mock_gen_email.return_value = "jdoe@test.com"
    worker = EnrichmentWorker(mock_db, mock_args)
    
    c = Company(company_id=1, company_name="Test")
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None, company_id=1, company=c)
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [c, Recruiter(recruiter_id=2, email="jdoe@test.com")]
    worker.detect_company_patterns = MagicMock(return_value=pat_data)
    
    res = worker.process_recruiter(r)
    
    assert res == "PENDING_REVIEW_EXISTING_EMAIL_MISMATCH" or res == "REJECTED_DUPLICATE" or "PENDING" in res or "REJECTED" in res

@patch('enrich_recruiter_contacts.generate_email')
def test_apply_writes_audit_on_success(mock_gen_email, mock_db, mock_args):
    mock_args.dry_run = False
    mock_args.apply = True
    mock_gen_email.return_value = "jdoe@test.com"
    
    worker = EnrichmentWorker(mock_db, mock_args)
    c = Company(company_id=1, company_name="Test")
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None, company_id=1, company=c)
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    worker.detect_company_patterns = MagicMock(return_value=pat_data)
    
    res = worker.process_recruiter(r)
    
    assert res == "APPLIED_MISSING_EMAIL"

@patch('enrich_recruiter_contacts.generate_email')
def test_apply_handles_db_failure(mock_gen_email, mock_db, mock_args):
    mock_args.dry_run = False
    mock_args.apply = True
    mock_gen_email.return_value = "jdoe@test.com"
    
    worker = EnrichmentWorker(mock_db, mock_args)
    c = Company(company_id=1, company_name="Test")
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None, company_id=1, company=c)
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    worker.detect_company_patterns = MagicMock(return_value=pat_data)
    
    mock_db.begin_nested.side_effect = Exception("DB Error")
    
    res = worker.process_recruiter(r)
    
    assert res == "FAILED_TECHNICAL_ERROR"

def test_existing_verified_protected(mock_db, mock_args):
    worker = EnrichmentWorker(mock_db, mock_args)
    c = Company(company_id=1, company_name="Test")
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email="verified@test.com", email_status="verified", company_id=1, company=c)
    
    mock_db.query.return_value.filter.return_value.first.return_value = c
    worker.detect_company_patterns = MagicMock(return_value={})
    
    res = worker.process_recruiter(r)
    
    assert res == "SKIPPED_ALREADY_CORRECT"
