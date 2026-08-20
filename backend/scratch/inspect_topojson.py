import requests
import json

url = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"
r = requests.get(url)
data = r.json()
print("Keys in TopoJSON:", data.keys())
objects = data.get("objects", {})
print("Objects keys:", objects.keys())
states = objects.get("states", {}).get("geometries", [])
print(f"Total state geometries: {len(states)}")
print("First 10 geometries:")
for g in states[:10]:
    print("  id:", repr(g.get("id")), "type:", type(g.get("id")), "properties:", g.get("properties"))

# Look at Washington (WA)
for g in states:
    if g.get("properties", {}).get("name") == "Washington":
        print("\nWashington geometry:", g)
