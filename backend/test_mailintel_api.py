import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath('C:\\TalentOpsAI\\backend'))

from fastapi.testclient import TestClient
from app.main import app
from app.routes.auth import get_current_user_from_request
from app.models.auth_models import User

# Mock user for testing
def override_get_current_user():
    user = User(id=1, email="admin@test.com", role_id=1)
    return user

app.dependency_overrides[get_current_user_from_request] = override_get_current_user

client = TestClient(app)

def test_api():
    print("Testing /mailintel/stats...")
    response = client.get("/mailintel/stats")
    assert response.status_code == 200, f"Stats failed: {response.text}"
    print("Stats Response:", response.json())
    
    print("\nTesting /mailintel/domains...")
    response = client.get("/mailintel/domains")
    assert response.status_code == 200, f"Domains failed: {response.text}"
    print("Domains Response:", response.json()[:2]) # print top 2
    
    print("\nTesting /mailintel/cleanup (dry run)...")
    response = client.post("/mailintel/cleanup", json={"confidence_less_than": -1})
    assert response.status_code == 200, f"Cleanup failed: {response.text}"
    print("Cleanup Response:", response.json())
    
    print("\nAll endpoints tested successfully.")

if __name__ == "__main__":
    test_api()
