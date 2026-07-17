import json

with open('backend/app/api_keys_pool.json', 'r') as f:
    data = json.load(f)

total_keys = len(data)
active_keys = sum(1 for k in data if k.get('status') == 'ACTIVE')
exhausted_keys = sum(1 for k in data if k.get('status') == 'EXHAUSTED')
total_usage = sum(k.get('usage_count', 0) for k in data)

print(f"Tavily API Keys:")
print(f"Total Keys: {total_keys}")
print(f"Active (With Credits): {active_keys}")
print(f"Exhausted (Zero Credits): {exhausted_keys}")
print(f"Total Lifetime API Calls: {total_usage}")
