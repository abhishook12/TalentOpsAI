import urllib.request
import re
import json

comp_ids = ['1681', '11056', '323296', '157324', '2937226', '2152', '14100', '3076', '72593', '23656', '21836', '40783', '8117', '62901', '112948', '5235', '6061', '18476', '19601', '11229', '21270', '26289', '3486', '58304', '18542', '6749', '2266', '65861', '25773', '50923', '8235', '13659', '19647', '60798', '2875', '49761', '50741', '59695', '47475', '74827', '55406', '52259', '96913', '47321', '43085', '30357', '35224', '79387', '15637', '44182', '79815', '27771', '43577', '77906', '53255', '4972', '41294', '46708', '71470', '21330', '78412', '13153', '37564', '2889', '89369', '48467', '55546', '32483', '20814', '35080', '70756', '46414', '51322', '19825', '56432', '60019', '77133', '69510', '21007', '22219', '16227', '13076', '15014', '20025', '51661', '34424', '14158', '51301']

print(f"Sampling {len(comp_ids)} company IDs from f_C filter...")

results = {}
for cid in comp_ids[:15]:
    url = f"https://www.linkedin.com/company/{cid}/"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            final_url = resp.geturl()
            # extract slug from final_url
            m = re.search(r"/company/([^/?]+)", final_url)
            slug = m.group(1) if m else final_url
            results[cid] = slug
    except Exception as e:
        results[cid] = f"error ({e})"

for cid, name in results.items():
    print(f"ID {cid:10s} -> {name}")
