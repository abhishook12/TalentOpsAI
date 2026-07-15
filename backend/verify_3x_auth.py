import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def verify_all():
    print("Starting 4x Verification (User Rule: 4 times local verification)")
    
    for i in range(1, 5):
        print(f"\n{'='*20}")
        print(f"VERIFICATION LOOP {i}")
        print(f"{'='*20}")
        
        # 1. Test Password Validation (Should fail with weak password)
        print("Testing POST /auth/register with weak password...")
        res = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": f"test{i}@test.com",
            "password": "123"
        })
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "password" in str(res.json()).lower() or "validation" in str(res.json()).lower() or "detail" in res.json()
        
        # 2. Test registration with good password to get tokens (testing hash logic)
        print("Testing POST /auth/register with strong password...")
        res = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": f"test_strong{i}@test.com",
            "password": "StrongPassword123!"
        })
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code in (200, 201)
        
        # We can't test frontend redirects easily via TestClient, but we can verify backend logic works
        print(f"Loop {i} completed successfully.\n")

if __name__ == "__main__":
    verify_all()
    print("ALL 4 VERIFICATION LOOPS COMPLETED SUCCESSFULLY.")
