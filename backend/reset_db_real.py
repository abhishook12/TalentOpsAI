import sys
print('Importing...')
try:
    import bcrypt
    from sqlalchemy import create_engine, text
except Exception as e:
    print('Import error:', e)
    sys.exit(1)

print('Connecting...')
DB_URL = 'postgresql+psycopg2://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
try:
    engine = create_engine(DB_URL, connect_args={'connect_timeout': 5})
    
    new_password = 'admin123456'
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with engine.begin() as conn:
        print('Querying...')
        res = conn.execute(text("SELECT id FROM users WHERE email = 'admin@talentops.com'")).fetchone()
        if not res:
            print('Admin user not found!')
        else:
            user_id = res[0]
            print(f'User found: {user_id}. Updating...')
            conn.execute(text("UPDATE users SET password_hash = :h, status = 'Active' WHERE id = :id"), {'h': hashed, 'id': user_id})
            conn.execute(text("DELETE FROM login_history WHERE user_id = :id"), {'id': user_id})
            print('Password updated to admin123456 and lockout cleared!')
except Exception as e:
    print('Error:', e)
