import requests

def test_counts():
    print("Testing 1: /analytics/companies-search")
    res1 = requests.get("http://localhost:8000/analytics/companies-search?q=Teksystems&limit=1&skip=0&min_recruiters=1").json()
    total_from_search = res1[0]['total_recruiters'] if res1 else 0
    active_from_search = res1[0]['active_recruiters'] if res1 else 0
    print(f"  Total: {total_from_search}")
    print(f"  Active: {active_from_search}")

    print("\nTesting 2: /analytics/company-states")
    res2 = requests.get("http://localhost:8000/analytics/company-states?company_id=42726").json()
    total_states_sum = sum(x['count'] for x in res2)
    print(f"  Total sum of all states: {total_states_sum}")

    print("\nTesting 3: /recruiters")
    res3 = requests.get("http://localhost:8000/recruiters?company_id=42726&page=1&limit=50")
    total_from_dir = res3.headers.get("x-total-count")
    print(f"  Total recruiters returned by directory API: {total_from_dir}")

    if int(total_from_search) == total_states_sum == int(total_from_dir):
        print("\nSUCCESS! All counts are perfectly synced!")
    else:
        print("\nFAILURE! Counts are mismatched!")

if __name__ == "__main__":
    test_counts()
