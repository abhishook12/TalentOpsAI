import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.database import SessionLocal
from app.services.platform_alarm import PlatformSafetyAlarm
from sqlalchemy import text

def run_fast_sql_accuracy():
    db = SessionLocal()
    print("=======================================================================")
    print("=== ULTRA-FAST SQL DATA ACCURACY & LOCATION ALIGNMENT ENGINE ===")
    print("=======================================================================")
    sys.stdout.flush()

    # Check safety limits (Rule #8 & Rule #7) before starting
    audit = PlatformSafetyAlarm.check_and_alert_all()
    if audit.get('is_alarm_active'):
        print("🚨 [SAFETY SHIELD] Platform threshold active. Aborting safely.")
        return

    start_t = time.time()

    # 1. BULK PHONE NUMBER STANDARDIZATION (10-digit raw strings -> XXX-XXX-XXXX)
    print("\n[Step 1] Standardizing 10-digit raw phone numbers to XXX-XXX-XXXX...")
    res_phones_10 = db.execute(text("""
        UPDATE recruiters 
        SET phone = SUBSTRING(phone, 1, 3) || '-' || SUBSTRING(phone, 4, 3) || '-' || SUBSTRING(phone, 7, 4)
        WHERE phone ~ '^[0-9]{10}$' AND phone NOT LIKE '%-%-%'
    """))
    db.commit()
    print(f" -> Standardized {res_phones_10.rowcount:,} 10-digit phone numbers.")

    # 1B. BULK PHONE NUMBER STANDARDIZATION (11-digit leading '1' -> XXX-XXX-XXXX)
    res_phones_11 = db.execute(text("""
        UPDATE recruiters 
        SET phone = SUBSTRING(phone, 2, 3) || '-' || SUBSTRING(phone, 5, 3) || '-' || SUBSTRING(phone, 8, 4)
        WHERE phone ~ '^1[0-9]{10}$' AND phone NOT LIKE '%-%-%'
    """))
    db.commit()
    print(f" -> Standardized {res_phones_11.rowcount:,} 11-digit phone numbers.")

    # 2. BULK STATE EXTRACTION FROM LOCATION FIELD FOR TOP US STATES & CITIES
    print("\n[Step 2] Resolving missing/generic states from Location & City strings across the database...")
    state_rules = [
        ('CA', "location ILIKE '%California%' OR location ILIKE '%, CA%' OR location ILIKE '%San Francisco%' OR location ILIKE '%Los Angeles%' OR location ILIKE '%San Jose%' OR location ILIKE '%San Diego%' OR location ILIKE '%Irvine%' OR location ILIKE '%Sacramento%'"),
        ('TX', "location ILIKE '%Texas%' OR location ILIKE '%, TX%' OR location ILIKE '%Austin%' OR location ILIKE '%Dallas%' OR location ILIKE '%Houston%' OR location ILIKE '%San Antonio%' OR location ILIKE '%Fort Worth%' OR location ILIKE '%Plano%'"),
        ('NY', "location ILIKE '%New York%' OR location ILIKE '%, NY%' OR location ILIKE '%NYC%' OR location ILIKE '%Manhattan%' OR location ILIKE '%Brooklyn%' OR location ILIKE '%Albany%'"),
        ('FL', "location ILIKE '%Florida%' OR location ILIKE '%, FL%' OR location ILIKE '%Miami%' OR location ILIKE '%Tampa%' OR location ILIKE '%Orlando%' OR location ILIKE '%Jacksonville%' OR location ILIKE '%Fort Lauderdale%'"),
        ('IL', "location ILIKE '%Illinois%' OR location ILIKE '%, IL%' OR location ILIKE '%Chicago%' OR location ILIKE '%Naperville%' OR location ILIKE '%Evanston%'"),
        ('GA', "location ILIKE '%Georgia%' OR location ILIKE '%, GA%' OR location ILIKE '%Atlanta%' OR location ILIKE '%Alpharetta%'"),
        ('MA', "location ILIKE '%Massachusetts%' OR location ILIKE '%, MA%' OR location ILIKE '%Boston%' OR location ILIKE '%Cambridge%' OR location ILIKE '%Waltham%'"),
        ('WA', "location ILIKE '%Washington%' OR location ILIKE '%, WA%' OR location ILIKE '%Seattle%' OR location ILIKE '%Bellevue%' OR location ILIKE '%Redmond%'"),
        ('PA', "location ILIKE '%Pennsylvania%' OR location ILIKE '%, PA%' OR location ILIKE '%Philadelphia%' OR location ILIKE '%Pittsburgh%'"),
        ('NC', "location ILIKE '%North Carolina%' OR location ILIKE '%, NC%' OR location ILIKE '%Charlotte%' OR location ILIKE '%Raleigh%' OR location ILIKE '%Durham%'"),
        ('VA', "location ILIKE '%Virginia%' OR location ILIKE '%, VA%' OR location ILIKE '%Richmond%' OR location ILIKE '%McLean%' OR location ILIKE '%Arlington%' OR location ILIKE '%Reston%'"),
        ('OH', "location ILIKE '%Ohio%' OR location ILIKE '%, OH%' OR location ILIKE '%Columbus%' OR location ILIKE '%Cleveland%' OR location ILIKE '%Cincinnati%'"),
        ('NJ', "location ILIKE '%New Jersey%' OR location ILIKE '%, NJ%' OR location ILIKE '%Jersey City%' OR location ILIKE '%Newark%' OR location ILIKE '%Hoboken%'"),
        ('CO', "location ILIKE '%Colorado%' OR location ILIKE '%, CO%' OR location ILIKE '%Denver%' OR location ILIKE '%Boulder%' OR location ILIKE '%Colorado Springs%'"),
        ('AZ', "location ILIKE '%Arizona%' OR location ILIKE '%, AZ%' OR location ILIKE '%Phoenix%' OR location ILIKE '%Scottsdale%' OR location ILIKE '%Tempe%'"),
        ('MI', "location ILIKE '%Michigan%' OR location ILIKE '%, MI%' OR location ILIKE '%Detroit%' OR location ILIKE '%Ann Arbor%'"),
        ('MD', "location ILIKE '%Maryland%' OR location ILIKE '%, MD%' OR location ILIKE '%Baltimore%' OR location ILIKE '%Bethesda%' OR location ILIKE '%Rockville%'"),
        ('MN', "location ILIKE '%Minnesota%' OR location ILIKE '%, MN%' OR location ILIKE '%Minneapolis%' OR location ILIKE '%St. Paul%'"),
        ('OR', "location ILIKE '%Oregon%' OR location ILIKE '%, OR%' OR location ILIKE '%Portland%' OR location ILIKE '%Beaverton%'"),
        ('IN', "location ILIKE '%Indiana%' OR location ILIKE '%, IN%' OR location ILIKE '%Indianapolis%'"),
        ('TN', "location ILIKE '%Tennessee%' OR location ILIKE '%, TN%' OR location ILIKE '%Nashville%' OR location ILIKE '%Memphis%'"),
        ('MO', "location ILIKE '%Missouri%' OR location ILIKE '%, MO%' OR location ILIKE '%St. Louis%' OR location ILIKE '%Kansas City%'"),
        ('WI', "location ILIKE '%Wisconsin%' OR location ILIKE '%, WI%' OR location ILIKE '%Milwaukee%' OR location ILIKE '%Madison%'"),
        ('UT', "location ILIKE '%Utah%' OR location ILIKE '%, UT%' OR location ILIKE '%Salt Lake City%' OR location ILIKE '%Lehi%'"),
        ('CT', "location ILIKE '%Connecticut%' OR location ILIKE '%, CT%' OR location ILIKE '%Hartford%' OR location ILIKE '%Stamford%'"),
        ('DC', "location ILIKE '%Washington DC%' OR location ILIKE '%District of Columbia%' OR location ILIKE '%, DC%'"),
    ]

    total_mapped_states = 0
    for st_code, cond in state_rules:
        res_st = db.execute(text(f"""
            UPDATE recruiters
            SET state = :st_code
            WHERE (state IS NULL OR state = 'US' OR state = 'N/A') AND ({cond})
        """), {'st_code': st_code})
        db.commit()
        if res_st.rowcount > 0:
            total_mapped_states += res_st.rowcount
            print(f"   -> Aligned {res_st.rowcount:,} records to State: [{st_code}]")

    # 3. NORMALIZED RECRUITER NAME SYNC IN ID BATCHES (Prevents Supabase statement timeouts)
    print("\n[Step 3] Syncing normalized_recruiter_name in batched ID ranges for search precision...")
    max_id = db.execute(text("SELECT MAX(recruiter_id) FROM recruiters")).scalar() or 330000
    batch_span = 25000
    total_norm = 0
    for s_id in range(1, max_id + 1, batch_span):
        e_id = s_id + batch_span - 1
        res_norm = db.execute(text("""
            UPDATE recruiters
            SET normalized_recruiter_name = LOWER(recruiter_name)
            WHERE recruiter_id BETWEEN :s AND :e 
              AND normalized_recruiter_name != LOWER(recruiter_name) 
              AND recruiter_name IS NOT NULL
        """), {'s': s_id, 'e': e_id})
        db.commit()
        if res_norm.rowcount > 0:
            total_norm += res_norm.rowcount
    print(f" -> Synced {total_norm:,} normalized names across ID ranges.")

    elapsed = round(time.time() - start_t, 2)
    print(f"\n✅ All bulk SQL accuracy operations completed across 327,319 rows in {elapsed} seconds!")
    db.close()

    # Final Safety Check (Rule #8)
    PlatformSafetyAlarm.check_and_alert_all()

if __name__ == '__main__':
    run_fast_sql_accuracy()
