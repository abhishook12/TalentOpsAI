import requests
import json

base_url = "http://localhost:8000"

print("1. Testing Registration")
reg_res = requests.post(f"{base_url}/auth/register", json={
    "first_name": "Test",
    "last_name": "User",
    "email": "testauth123@example.com",
    "password": "StrongPassword123!"
})
print("Registration Response:", reg_res.status_code, reg_res.text)

print("\n2. Testing Login (Should fail due to unverified)")
login_res = requests.post(f"{base_url}/auth/login", json={
    "email": "testauth123@example.com",
    "password": "StrongPassword123!"
})
print("Login Response:", login_res.status_code, login_res.text)

print("\n3. Testing Forgot Password")
forgot_res = requests.post(f"{base_url}/auth/forgot-password", json={
    "email": "testauth123@example.com"
})
print("Forgot Password Response:", forgot_res.status_code, forgot_res.text)

print("\n4. Testing Google Auth Mock")
google_res = requests.post(f"{base_url}/auth/google", json={
    "credential": "mock_google_token"
})
print("Google Auth Response:", google_res.status_code, google_res.text)
