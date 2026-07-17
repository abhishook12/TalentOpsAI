import requests

def test_endpoints():
    print("Test 1: Notifications")
    r1 = requests.post("http://localhost:8000/notifications/test")
    if r1.status_code == 200:
        print("Test 1 Passed")
    else:
        print("Test 1 Failed", r1.status_code, r1.text)
        
    print("Test 2: Dashboard Insights")
    r2 = requests.get("http://localhost:8000/analytics/insights")
    if r2.status_code == 200:
        print("Test 2 Passed")
    else:
        print("Test 2 Failed", r2.status_code, r2.text)
        
    print("Test 3: Background Jobs")
    r3 = requests.get("http://localhost:8000/admin/jobs")
    if r3.status_code == 200:
        print("Test 3 Passed")
    else:
        print("Test 3 Failed", r3.status_code, r3.text)
        
    print("Test 4: Audit Logs")
    r4 = requests.get("http://localhost:8000/admin/audit-logs")
    if r4.status_code == 200:
        print("Test 4 Passed")
    else:
        print("Test 4 Failed", r4.status_code, r4.text)

if __name__ == '__main__':
    test_endpoints()
