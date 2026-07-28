import sqlite3
import psycopg
import sys

# Connect to SQLite
sl_conn = sqlite3.connect(r'C:\TalentOpsAI\backend\dev.db')
sl_conn.row_factory = sqlite3.Row
sl_c = sl_conn.cursor()

# Connect to Supabase
pg_conn = psycopg.connect('postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
pg_c = pg_conn.cursor()

try:
    print("Starting migration of recent local uploads to production...")

    # 1. Migrate Companies
    sl_c.execute("SELECT * FROM companies")
    companies = sl_c.fetchall()

    if companies:
        print(f"Migrating {len(companies)} companies...")
        # We need to map SQLite company_id to Supabase company_id after insert
        comp_id_mapping = {}
        def trunc(val, max_len=150):
            return str(val)[:max_len] if val is not None else None

        for i, comp in enumerate(companies):
            try:
                pg_c.execute("""
                    INSERT INTO companies (user_id, company_name, normalized_company_name, industry, location, state, website, linkedin_url, is_active, is_tracked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING company_id
                """, (comp['user_id'], trunc(comp['company_name'], 255), trunc(comp['normalized_company_name'], 255), trunc(comp['industry'], 100), trunc(comp['location'], 150), comp['state'], trunc(comp['website'], 255), trunc(comp['linkedin_url'], 255), bool(comp['is_active']), bool(comp['is_tracked'])))
                
                res = pg_c.fetchone()
                if res:
                    comp_id_mapping[comp['company_id']] = res[0]
            except Exception as e:
                pg_conn.rollback()
                pass
                
            if (i + 1) % 100 == 0:
                pg_conn.commit()
                
        pg_conn.commit()

    # 2. Migrate Recruiters
    sl_c.execute("SELECT * FROM recruiters")
    recruiters = sl_c.fetchall()

    if recruiters:
        print(f"Migrating {len(recruiters)} recruiters...")
        
        insert_query = """
            INSERT INTO recruiters (user_id, recruiter_name, normalized_recruiter_name, email, phone, linkedin, specialization, title, notes, company_id, location, state, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """
        
        for i, r in enumerate(recruiters):
            new_comp_id = comp_id_mapping.get(r['company_id']) if r['company_id'] else None
            try:
                pg_c.execute(insert_query, (
                    r['user_id'], 
                    trunc(r['recruiter_name'], 150), 
                    trunc(r['normalized_recruiter_name'], 150), 
                    trunc(r['email'], 150), 
                    trunc(r['phone'], 30), 
                    trunc(r['linkedin'], 255), 
                    trunc(r['specialization'], 150), 
                    trunc(r['title'], 150), 
                    r['notes'], 
                    new_comp_id, 
                    trunc(r['location'], 255), 
                    r['state'], 
                    r['created_at']
                ))
            except Exception as e:
                pg_conn.rollback()
                pass
                
            if (i + 1) % 500 == 0:
                pg_conn.commit()
                
        pg_conn.commit()

    pg_conn.commit()
    print("Migration complete! Production database is now fully updated with all local uploads.")

except Exception as e:
    pg_conn.rollback()
    print(f"Migration failed: {e}")

finally:
    sl_conn.close()
    pg_conn.close()
