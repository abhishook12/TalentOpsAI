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
    return args

def test_omitted_limit_processes_all(mock_db, mock_args):
    # Setup
    worker = EnrichmentWorker(mock_db, mock_args)
    mock_query = mock_db.query.return_value
    mock_query.all.return_value = [Company(company_name="Test")]
    
    # Act
    worker.run()
    
    # Assert
    mock_query.limit.assert_not_called()
    mock_query.all.assert_called()

def test_company_limit(mock_db, mock_args):
    mock_args.company_limit = 5
    worker = EnrichmentWorker(mock_db, mock_args)
    mock_query = mock_db.query.return_value
    
    worker.run()
    
    mock_query.limit.assert_called_with(5)

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
    
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None)
    c = Company(company_id=1, company_name="Test")
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    mock_filter = mock_db.query.return_value.filter.return_value
    mock_filter.first.return_value = Recruiter(recruiter_id=2, email="jdoe@test.com") # Conflict
    
    worker.process_recruiter(r, c, pat_data)
    
    assert worker.stats["rejected_duplicate_email"] == 1
    assert worker.stats["database_changes"] == 0
    assert worker.stats["proposed_updates"] == 0

@patch('enrich_recruiter_contacts.generate_email')
def test_apply_writes_audit_on_success(mock_gen_email, mock_db, mock_args):
    mock_args.dry_run = False
    mock_args.apply = True
    mock_gen_email.return_value = "jdoe@test.com"
    
    worker = EnrichmentWorker(mock_db, mock_args)
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None)
    c = Company(company_id=1, company_name="Test")
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    # No conflict
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    worker.process_recruiter(r, c, pat_data)
    
    assert worker.stats["valid_candidates"] == 1
    assert worker.stats["database_changes"] == 1
    assert worker.stats["audit_changes"] == 1
    mock_db.commit.assert_called()

@patch('enrich_recruiter_contacts.generate_email')
def test_apply_handles_db_failure(mock_gen_email, mock_db, mock_args):
    mock_args.dry_run = False
    mock_args.apply = True
    mock_gen_email.return_value = "jdoe@test.com"
    
    worker = EnrichmentWorker(mock_db, mock_args)
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email=None)
    c = Company(company_id=1, company_name="Test")
    pat_data = {'domain': 'test.com', 'pattern': '{first}{last}', 'confidence': 80, 'count': 5, 'match_pct': 100}
    
    # No conflict
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    # Simulate DB error on commit
    mock_db.commit.side_effect = [Exception("DB Error"), None]
    
    worker.process_recruiter(r, c, pat_data)
    
    assert worker.stats["database_changes"] == 0
    mock_db.rollback.assert_called()
    # It should still write a failure audit
    assert worker.stats["audit_changes"] == 1

def test_existing_verified_protected(mock_db, mock_args):
    worker = EnrichmentWorker(mock_db, mock_args)
    r = Recruiter(recruiter_id=1, recruiter_name="John Doe", email="verified@test.com", email_status="verified")
    c = Company(company_id=1, company_name="Test")
    
    worker.process_recruiter(r, c, {})
    
    assert worker.stats["skipped_existing_verified"] == 1
