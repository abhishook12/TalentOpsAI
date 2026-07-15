import requests

url = "http://localhost:8000/auth/login"
payload = {
    "email": "abhishekjadon706@gmail.com",
    "password": "Kx7!mQp2",
    "remember_me": False
}
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
