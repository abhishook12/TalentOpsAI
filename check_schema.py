from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
with engine.connect() as conn:
    print("RECRUITERS SCHEMA:")
    for row in conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recruiters';")).fetchall():
        print(f"{row[0]}: {row[1]}")
    
    print("\nCOMPANIES SCHEMA:")
    for row in conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'companies';")).fetchall():
        print(f"{row[0]}: {row[1]}")
