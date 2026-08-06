import sys
try:
    from sqlalchemy import create_engine, text
    DB_URL = 'postgresql+psycopg2://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    engine = create_engine(DB_URL, connect_args={'connect_timeout': 5})
    with engine.begin() as conn:
        print('Top 5 domains for unknown recruiters and their known state distribution:')
        domains = conn.execute(text("SELECT SPLIT_PART(email, '@', 2) as domain, COUNT(*) FROM recruiters r WHERE (r.state IS NULL OR r.state = '') AND (r.location IS NULL OR r.location = '') AND (r.phone IS NULL OR r.phone = '') GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 5")).fetchall()
        for d in domains:
            domain = d[0]
            print(f"\nDomain: {domain} (Unknown count: {d[1]})")
            states = conn.execute(text("SELECT state, COUNT(*) FROM recruiters WHERE SPLIT_PART(email, '@', 2) = :domain AND state IS NOT NULL AND state != '' AND state != 'US' GROUP BY state ORDER BY COUNT(*) DESC LIMIT 3"), {"domain": domain}).fetchall()
            for s in states:
                print(f"  - {s[0]}: {s[1]}")
except Exception as e:
    print('Error:', e)
