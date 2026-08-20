import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store

recruiter_store._ensure_loaded()
conn = recruiter_store._conn

def run_test_query(query, state=None):
    clean_q = "".join(c for c in (query or "").lower() if c.isalnum())
    tokens = [t.strip().lower() for t in (query or "").split() if t.strip()]
    
    if state and state.upper() != "ALL":
        where = ["state_upper = ?"]
        params = [state.upper()]
        
        token_conds = []
        for t in tokens:
            token_conds.append("(LOWER(cs.company_key) LIKE ? OR LOWER(COALESCE(co.dominant_domain, '')) LIKE ?)")
            params.extend([f"%{t}%", f"%{t}%"])
        
        fuzzy_cond = f"""(
            ({' AND '.join(token_conds)})
            OR LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')) LIKE '%{clean_q}%'
            OR LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')) LIKE '%{clean_q}%'
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')), '{clean_q}') > 0.80
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') > 0.80
        )"""
        where.append(fuzzy_cond)
        
        sql = f"""
            SELECT
                cs.company_key,
                SUM(cs.recruiter_count) AS recruiter_count,
                COALESCE(co.dominant_domain, MAX(cs.dominant_domain)) AS dominant_domain
            FROM company_summary cs
            LEFT JOIN company_overall co ON cs.company_key = co.company_key
            WHERE {' AND '.join(where)}
            GROUP BY cs.company_key, co.dominant_domain
            ORDER BY 
                GREATEST(
                    jaro_winkler_similarity(LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')), '{clean_q}'),
                    jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}')
                ) >= 0.88 DESC,
                recruiter_count DESC,
                cs.company_key ASC
            LIMIT 5
        """
    else:
        where = ["1=1"]
        params = []
        token_conds = []
        for t in tokens:
            token_conds.append("(LOWER(company_key) LIKE ? OR LOWER(COALESCE(dominant_domain, '')) LIKE ?)")
            params.extend([f"%{t}%", f"%{t}%"])
            
        fuzzy_cond = f"""(
            ({' AND '.join(token_conds)})
            OR LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')) LIKE '%{clean_q}%'
            OR LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')) LIKE '%{clean_q}%'
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}') > 0.80
            OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') > 0.80
        )"""
        where.append(fuzzy_cond)
        
        sql = f"""
            SELECT
                company_key,
                recruiter_count,
                dominant_domain
            FROM company_overall
            WHERE {' AND '.join(where)}
            ORDER BY 
                GREATEST(
                    jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}'),
                    jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}')
                ) >= 0.88 DESC,
                recruiter_count DESC,
                company_key ASC
            LIMIT 5
        """
        
    rows = conn.execute(sql, params).fetchall()
    print(f"\nQuery: '{query}' (State: {state}) -> {len(rows)} results:")
    for r in rows:
        print(f"  - Key: {r[0]} | Count: {r[1]} | Dom: {r[2]}")

run_test_query("blustone")
run_test_query("blueStone")
run_test_query("bluestone", state="FL")
run_test_query("robrt half")
run_test_query("aerotec")
run_test_query("instight global")
run_test_query("man power")
run_test_query("teksystem")
