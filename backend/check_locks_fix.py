from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
with engine.connect() as conn:
    r = conn.execute(text("SELECT classid, objid, mode, granted FROM pg_locks WHERE locktype = 'advisory'")).fetchall()
    print('Advisory locks:', r)
    r2 = conn.execute(text('SELECT pg_try_advisory_lock(83726491)')).scalar()
    print('Lock acquired:', r2)
    if r2:
        conn.execute(text('SELECT pg_advisory_unlock(83726491)'))
        print('Released lock so the backend can take it on restart.')
