import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store

recruiter_store._ensure_loaded()
conn = recruiter_store._conn

test_queries = [
    "blustone",           # typo for bluestone
    "blue stone",         # space variation
    "robrt half",         # typo for robert half
    "half robert",        # word order reversed
    "insigt global",      # typo for insight global
    "man power",          # space variation
    "aerotec",            # typo for aerotek
    "teksystem",          # singular/plural
    "ranstad",            # typo for randstad
    "beacon hil",         # typo for beacon hill
]

for q in test_queries:
    tokens = [t.strip().lower() for t in q.split() if t.strip()]
    conds = []
    params = []
    
    # 1. Exact or substring on unspaced alphanumeric
    clean_q = "".join(c for c in q.lower() if c.isalnum())
    
    # 2. Token conditions
    for t in tokens:
        conds.append("(LOWER(company_key) LIKE ? OR LOWER(COALESCE(dominant_domain, '')) LIKE ?)")
        params.extend([f"%{t}%", f"%{t}%"])
        
    print(f"\n================ Testing Query: '{q}' ================")
    # Let's test DuckDB Jaro-Winkler and Levenshtein
    rows = conn.execute(f"""
        SELECT 
            company_key,
            recruiter_count,
            dominant_domain,
            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}') as jw_key,
            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') as jw_dom
        FROM company_overall
        WHERE 
            ({' AND '.join(conds)})
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}') > 0.75
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') > 0.75
            OR LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')) LIKE '%{clean_q}%'
        ORDER BY GREATEST(
            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}'),
            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}')
        ) DESC, recruiter_count DESC
        LIMIT 5
    """, params).fetchall()
    
    for r in rows:
        print(f"  -> Key: {r[0]} | Count: {r[1]} | Dom: {r[2]} | JW_Key: {r[3]:.2f} | JW_Dom: {r[4]:.2f}")
