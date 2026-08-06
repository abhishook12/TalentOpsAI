import sys
try:
    from sqlalchemy import create_engine, text
    DB_URL = 'postgresql+psycopg2://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    engine = create_engine(DB_URL, connect_args={'connect_timeout': 5})
    with engine.begin() as conn:
        print('Top 10 company IDs for remaining unknown recruiters:')
        cids = conn.execute(text("SELECT company_id, COUNT(*) FROM recruiters WHERE state IS NULL OR state = '' GROUP BY company_id ORDER BY COUNT(*) DESC LIMIT 10")).fetchall()
        for c in cids:
            if c[0] is not None:
                comp = conn.execute(text("SELECT name, state FROM companies WHERE company_id = :cid"), {"cid": c[0]}).fetchone()
                print(f"ID {c[0]} (Count: {c[1]}) -> {comp}")
            else:
                print(f"ID None (Count: {c[1]})")
except Exception as e:
    print('Error:', e)
