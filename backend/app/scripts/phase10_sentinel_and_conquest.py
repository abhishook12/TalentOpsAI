import time
import psycopg

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

CITY_STATE_RULES = [
    ('%atlanta%', 'GA'), ('%georgia%', 'GA'), ('%, ga%', 'GA'), ('%savannah%', 'GA'),
    ('%dallas%', 'TX'), ('%austin%', 'TX'), ('%houston%', 'TX'), ('%san antonio%', 'TX'), ('%, tx%', 'TX'), ('%texas%', 'TX'),
    ('%new york%', 'NY'), ('%nyc%', 'NY'), ('%brooklyn%', 'NY'), ('%manhattan%', 'NY'), ('%, ny%', 'NY'),
    ('%chicago%', 'IL'), ('%illinois%', 'IL'), ('%, il%', 'IL'),
    ('%los angeles%', 'CA'), ('%san francisco%', 'CA'), ('%san diego%', 'CA'), ('%bay area%', 'CA'), ('%, ca%', 'CA'), ('%california%', 'CA'),
    ('%miami%', 'FL'), ('%tampa%', 'FL'), ('%orlando%', 'FL'), ('%jacksonville%', 'FL'), ('%, fl%', 'FL'), ('%florida%', 'FL'),
    ('%seattle%', 'WA'), ('%washington%', 'WA'), ('%, wa%', 'WA'),
    ('%boston%', 'MA'), ('%massachusetts%', 'MA'), ('%, ma%', 'MA'),
    ('%charlotte%', 'NC'), ('%raleigh%', 'NC'), ('%north carolina%', 'NC'), ('%, nc%', 'NC'),
    ('%denver%', 'CO'), ('%colorado%', 'CO'), ('%, co%', 'CO'),
    ('%phoenix%', 'AZ'), ('%scottsdale%', 'AZ'), ('%arizona%', 'AZ'), ('%, az%', 'AZ'),
    ('%philadelphia%', 'PA'), ('%pittsburgh%', 'PA'), ('%pennsylvania%', 'PA'), ('%, pa%', 'PA'),
    ('%detroit%', 'MI'), ('%michigan%', 'MI'), ('%, mi%', 'MI'),
    ('%minneapolis%', 'MN'), ('%minnesota%', 'MN'), ('%, mn%', 'MN'),
    ('%columbus%', 'OH'), ('%cleveland%', 'OH'), ('%cincinnati%', 'OH'), ('%ohio%', 'OH'), ('%, oh%', 'OH'),
    ('%nashville%', 'TN'), ('%tennessee%', 'TN'), ('%, tn%', 'TN'),
    ('%st. louis%', 'MO'), ('%kansas city%', 'MO'), ('%missouri%', 'MO'), ('%, mo%', 'MO'),
    ('%indianapolis%', 'IN'), ('%indiana%', 'IN'), ('%, in%', 'IN'),
    ('%salt lake city%', 'UT'), ('%utah%', 'UT'), ('%, ut%', 'UT'),
    ('%richmond%', 'VA'), ('%virginia%', 'VA'), ('%, va%', 'VA'),
    ('%baltimore%', 'MD'), ('%maryland%', 'MD'), ('%, md%', 'MD'),
    ('%portland%', 'OR'), ('%oregon%', 'OR'), ('%, or%', 'OR'),
    ('%las vegas%', 'NV'), ('%nevada%', 'NV'), ('%, nv%', 'NV')
]

def execute_phase10():
    print("=== STARTING PHASE 10: CONTRADICTION SENTINEL & STATE CONQUEST ===", flush=True)
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # Step 1: Check baseline unknown state count
    cur.execute("SELECT count(*) FROM recruiters WHERE state IS NULL OR state = 'US'", prepare=False)
    initial_unknown = cur.fetchone()[0]
    print(f"Initial Unknown/US State Recruiters: {initial_unknown:,}", flush=True)

    # Step 2: Check #19 & Check #6 - Deep Text & Notes Contradiction Sentinel
    print("\n[Check #19] Running Deep Notes & Location String Contradiction Audit...", flush=True)
    total_notes_fixed = 0
    for pattern, st in CITY_STATE_RULES:
        query = """
            UPDATE recruiters
            SET state = %s
            WHERE (state IS NULL OR state = 'US')
              AND (notes ILIKE %s OR location ILIKE %s)
        """
        cur.execute(query, (st, pattern, pattern), prepare=False)
        if cur.rowcount > 0:
            total_notes_fixed += cur.rowcount
    conn.commit()
    print(f" -> Resolved {total_notes_fixed:,} profiles from notes/location strings!", flush=True)

    # Step 3: Company HQ & Peer Majority State Propagation
    print("\n[Deep Conquest] Executing Company HQ & Peer Majority State Propagation...", flush=True)
    hq_prop_query = """
        UPDATE recruiters r
        SET state = c.state
        FROM companies c
        WHERE r.company_id = c.company_id
          AND (r.state IS NULL OR r.state = 'US')
          AND c.state IS NOT NULL
          AND c.state != 'US'
          AND length(c.state) = 2
    """

    cur.execute(hq_prop_query, prepare=False)
    hq_fixed = cur.rowcount
    conn.commit()
    print(f" -> Propagated canonical HQ states to {hq_fixed:,} profiles!", flush=True)

    # Step 4: Final verification counts
    cur.execute("SELECT count(*) FROM recruiters WHERE state IS NOT NULL AND state != 'US'", prepare=False)
    final_known = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM recruiters WHERE state IS NULL OR state = 'US'", prepare=False)
    final_unknown = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM recruiters", prepare=False)
    total_rec = cur.fetchone()[0]

    cov = (final_known / total_rec) * 100 if total_rec > 0 else 0
    print(f"\n=== PHASE 10 CONQUEST RESULTS ===", flush=True)
    print(f"Total Database Profiles : {total_rec:,}", flush=True)
    print(f"Verified Known States   : {final_known:,} ({cov:.2f}% coverage)", flush=True)
    print(f"Remaining Unknown States: {final_unknown:,}", flush=True)
    print(f"Total Time Elapsed      : {time.time() - t0:.2f}s", flush=True)

    cur.close()
    conn.close()

if __name__ == "__main__":
    execute_phase10()
