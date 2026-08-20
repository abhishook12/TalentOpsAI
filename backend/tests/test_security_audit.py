import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.auth_models import User
from app.services.auth_service import create_access_token

# Test DB Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sec_audit.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_sec_audit.db"):
        try:
            os.remove("./test_sec_audit.db")
        except Exception:
            pass

@pytest.fixture
def test_user():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="sec_audit_user@example.com").first()
    if not user:
        user = User(email="sec_audit_user@example.com", first_name="Sec", last_name="User", password_hash="hash", status="Active")
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_notifications_endpoint_requires_auth():
    # Without token
    res = client.get("/notifications/")
    assert res.status_code == 401

def test_notifications_with_auth(auth_headers):
    res = client.get("/notifications/", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_talent_pools_requires_auth():
    res = client.get("/talent-pools/")
    assert res.status_code == 401

def test_campaigns_requires_auth():
    res = client.get("/campaigns/")
    assert res.status_code == 401

def test_action_log_with_auth(auth_headers, test_user):
    payload = {"action_type": "view_dashboard", "details": {"tab": "overview"}, "status": "success"}
    res = client.post("/actions/log", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True

def test_mailintel_domain_reputation_requires_auth():
    res = client.get("/mailintel/domains")
    assert res.status_code == 401
