import pytest
import os
os.environ["MOCK_OAUTH"] = "True"
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.auth_models import User, ConnectedEmailAccount, UserBridgeStatus
from app.models.campaigns import Campaign, EmailLog, EmailLogStatus

# Setup Test Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_bridge_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_bridge_v2.db"):
        try:
            os.remove("./test_bridge_v2.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_user(db_session):
    user = db_session.query(User).filter_by(email="test_oauth@example.com").first()
    if not user:
        user = User(email="test_oauth@example.com", first_name="Test", last_name="Test", password_hash="hashed", status="Active")
        db_session.add(user)
    else:
        user.status = "Active"
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    from app.services.auth_service import create_access_token
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_oauth_login_redirect(auth_headers):
    # Test 1: Connect Outlook with Microsoft OAuth initiates
    res = client.get("/bridge/oauth/login?redirect_uri=/test", headers=auth_headers, follow_redirects=False)
    assert res.status_code == 307
    assert "oauth/callback" in res.headers["location"] or "login.microsoftonline.com" in res.headers["location"]

def test_oauth_callback(auth_headers, test_user, db_session):
    # Setup state
    import jwt
    from app.services.auth_service import SECRET_KEY, ALGORITHM
    import datetime
    from app.routes import bridge
    bridge.MOCK_OAUTH = True
    
    state = jwt.encode({"user_id": test_user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(state, bytes):
        state = state.decode('utf-8')
    
    # Test 2: OAuth Callback creates ConnectedEmailAccount
    res = client.get(f"/bridge/oauth/callback?code=mock123&state={state}", headers=auth_headers, follow_redirects=False)
    if res.status_code != 307:
        print("CALLBACK ERROR TEXT:", res.text)
    assert res.status_code == 307  # Redirects back to app
    
    account = db_session.query(ConnectedEmailAccount).filter_by(user_id=test_user.id).first()
    assert account is not None
    assert account.email_address == test_user.email
    assert account.status == "connected"
    
def test_bridge_tasks_unauthorized(test_user):
    # No auth
    res = client.get("/bridge/tasks")
    assert res.status_code == 401

def test_bridge_tasks_and_results_flow(auth_headers, test_user, db_session):
    # 1. Queue an email offline
    c = Campaign(user_id=test_user.id, name="Test", status="active", from_email=test_user.email)
    db_session.add(c)
    db_session.commit()
    
    log = EmailLog(campaign_id=c.campaign_id, recipient_email="target@example.com", status="sending", sent_via="outlook_bridge")
    db_session.add(log)
    db_session.commit()
    
    # 2. Bridge connects and pulls tasks (Offline Recovery)
    res = client.get("/bridge/tasks", headers=auth_headers)
    assert res.status_code == 200
    tasks = res.json().get("tasks")
    assert len(tasks) == 1
    assert tasks[0]["to_email"] == "target@example.com"
    
    # 3. Bridge posts success result (Single Email Send / Delivery Confirmation)
    log_id = tasks[0]["log_id"]
    payload = {"results": [{"log_id": log_id, "success": True}]}
    res = client.post("/bridge/results", json=payload, headers=auth_headers)
    assert res.status_code == 200
    
    # Check DB
    db_session.refresh(log)
    assert log.status == EmailLogStatus.delivered.value
    assert log.outlook_accepted is True

def test_bridge_disconnect(auth_headers, test_user, db_session):
    # Test Disconnect Outlook
    res = client.post("/bridge/disconnect", headers=auth_headers)
    assert res.status_code == 200
    
    account = db_session.query(ConnectedEmailAccount).filter_by(user_id=test_user.id).first()
    assert account.status == "disconnected"
    assert account.access_token is None
