import requests

test_domains = [
    'roberthalf.com',
    'teksystems.com',
    'insightglobal.com',
    'optomi.com',
    'randstadusa.com',
    'randstad.com',
    'manpowergroup.com',
    'manpower.com',
    'beaconhillstaffing.com',
    'actalentservices.com',
    'actalent.com',
    'kforce.com',
    'aerotek.com',
    'apexsystems.com',
    'kellyservices.com',
    'cybercoders.com',
    'collabera.com',
    'judge.com'
]

print("=== TESTING LOGO AVAILABILITY ACROSS TIERS ===")
for d in test_domains:
    h_url = f"https://logos.hunter.io/{d}"
    t_url = f"https://logo.tomba.io/{d}?size=128"
    e_url = f"https://api.companyenrich.com/logo/{d}"
    g_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{d}&size=128"
    
    h_status = "FAIL"
    try:
        r = requests.get(h_url, timeout=4)
        h_status = f"HTTP {r.status_code} ({len(r.content)} bytes)" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        h_status = str(e)[:30]
        
    t_status = "FAIL"
    try:
        r = requests.get(t_url, timeout=4)
        t_status = f"HTTP {r.status_code} ({len(r.content)} bytes)" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        t_status = str(e)[:30]

    g_status = "FAIL"
    try:
        r = requests.get(g_url, timeout=4)
        g_status = f"HTTP {r.status_code} ({len(r.content)} bytes)" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        g_status = str(e)[:30]

    print(f"{d:25} | Hunter: {h_status:30} | Tomba: {t_status:25} | Google: {g_status}")
