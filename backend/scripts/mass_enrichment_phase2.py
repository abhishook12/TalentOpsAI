import os
import time
import psycopg
from dotenv import load_dotenv

def run_phase2_enrichment():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SET statement_timeout = 0;")

    print("=" * 80)
    print("MASS FREE ENRICHMENT ENGINE PHASE 2 (INTERNAL INFERENCE & TAXONOMY)")
    print("=" * 80)
    start_total = time.time()

    def update_batched(query, params, batch_size=25000, desc=""):
        total_updated = 0
        while True:
            batched_query = f"""
                WITH batch AS (
                    {query}
                    LIMIT {batch_size}
                )
                UPDATE {params['table']} t
                SET {params['set_clause']}
                FROM batch
                WHERE t.{params['pk']} = batch.{params['pk']}
            """
            cursor.execute(batched_query, params.get('args', ()))
            rows = cursor.rowcount
            conn.commit()
            total_updated += rows
            if rows < batch_size:
                break
        print(f" -> {desc}: {total_updated:,} rows updated.")
        return total_updated

    # =========================================================================
    # ITEM 1: Fill Recruiter Taxonomy Category from Specialization
    # =========================================================================
    print("\n[Item 1/6] Auto-filling Recruiter Taxonomy Category...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id, specialization as new_tax
            FROM recruiters
            WHERE (taxonomy_category IS NULL OR taxonomy_category = '' OR LOWER(taxonomy_category) IN ('null','n/a','none'))
              AND specialization IS NOT NULL AND specialization != '' AND LOWER(specialization) NOT IN ('null','n/a','none','unknown')
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'taxonomy_category = batch.new_tax'},
        batch_size=25000,
        desc="Taxonomy Categories filled from specialization"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 2: Fill Company Data Source
    # =========================================================================
    print("\n[Item 2/6] Tagging Company Data Source as 'teams_extractor'...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT company_id
            FROM companies
            WHERE data_source IS NULL OR data_source = '' OR LOWER(data_source) IN ('null','n/a','none')
        """,
        params={'table': 'companies', 'pk': 'company_id', 'set_clause': "data_source = 'teams_extractor'"},
        batch_size=25000,
        desc="Company Data Source tagged"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 3: Compute Recruiter Completeness Score for remaining rows
    # =========================================================================
    print("\n[Item 3/6] Computing Completeness Score where missing...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id,
            LEAST(100, GREATEST(0,
                CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE 'scrubbed-%%' THEN 30 ELSE 0 END +
                CASE WHEN title IS NOT NULL AND title != '' THEN 25 ELSE 0 END +
                CASE WHEN company_id IS NOT NULL THEN 20 ELSE 0 END +
                CASE WHEN location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none','unknown') THEN 15 ELSE 0 END +
                CASE WHEN state IS NOT NULL AND state != '' AND LOWER(state) NOT IN ('null','n/a','none','unknown') THEN 10 ELSE 0 END
            )) as calc_comp
            FROM recruiters
            WHERE completeness_score IS NULL OR completeness_score = 0
        """,
        params={'table': 'recruiters', 'pk': 'recruiter_id', 'set_clause': 'completeness_score = batch.calc_comp'},
        batch_size=25000,
        desc="Completeness Score computed"
    )
    print(f" -> Completed in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 4: Infer Company State from majority Recruiter State
    # =========================================================================
    print("\n[Item 4/6] Inferring Company State from majority Recruiter State...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies c
        SET state = sub.top_state
        FROM (
            SELECT company_id, state as top_state
            FROM (
                SELECT company_id, state, COUNT(*) as cnt,
                       ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY COUNT(*) DESC) as rn
                FROM recruiters
                WHERE state IS NOT NULL AND state != '' AND LOWER(state) NOT IN ('null','n/a','none','unknown')
                GROUP BY company_id, state
            ) ranked
            WHERE rn = 1 AND cnt >= 2
        ) sub
        WHERE c.company_id = sub.company_id
          AND (c.state IS NULL OR c.state = '' OR LOWER(c.state) IN ('null','n/a','none'))
    """)
    print(f" -> Company State inferred for {cursor.rowcount:,} companies in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # ITEM 5: Infer Company HQ Location from majority Recruiter City
    # =========================================================================
    print("\n[Item 5/6] Inferring Company HQ Location from majority Recruiter City...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies c
        SET location = sub.top_loc
        FROM (
            SELECT company_id, location as top_loc
            FROM (
                SELECT company_id, location, COUNT(*) as cnt,
                       ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY COUNT(*) DESC) as rn
                FROM recruiters
                WHERE location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none','unknown')
                GROUP BY company_id, location
            ) ranked
            WHERE rn = 1 AND cnt >= 2
        ) sub
        WHERE c.company_id = sub.company_id
          AND (c.location IS NULL OR c.location = '' OR LOWER(c.location) IN ('null','n/a','none'))
    """)
    print(f" -> Company HQ inferred for {cursor.rowcount:,} companies in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # ITEM 6: Infer Recruiter State from top US Cities
    # =========================================================================
    print("\n[Item 6/6] Inferring missing Recruiter States from top US Cities...")
    t0 = time.time()
    cursor.execute("""
        UPDATE recruiters
        SET state = CASE
            WHEN LOWER(location) ~ 'austin|dallas|houston|san antonio|fort worth|el paso|arlington|plano' THEN 'TX'
            WHEN LOWER(location) ~ 'san francisco|los angeles|san diego|sanjose|san jose|sacramento|oakland|irvine|palo alto|mountain view|santa clara|sunnyvale' THEN 'CA'
            WHEN LOWER(location) ~ 'new york|nyc|brooklyn|manhattan|queens|bronx|staten island|buffalo|rochester|albany' THEN 'NY'
            WHEN LOWER(location) ~ 'chicago|naperville|peoria|rockford|aurora' THEN 'IL'
            WHEN LOWER(location) ~ 'atlanta|savannah|augusta|alpharetta' THEN 'GA'
            WHEN LOWER(location) ~ 'boston|cambridge|waltham|somerville|worcester' THEN 'MA'
            WHEN LOWER(location) ~ 'seattle|bellevue|redmond|tacoma|spokane|kirkland' THEN 'WA'
            WHEN LOWER(location) ~ 'miami|tampa|orlando|jacksonville|fort lauderdale|boca raton|st\. petersburg' THEN 'FL'
            WHEN LOWER(location) ~ 'denver|boulder|colorado springs|aurora|fort collins' THEN 'CO'
            WHEN LOWER(location) ~ 'raleigh|charlotte|durham|chapel hill|greensboro|winston-salem' THEN 'NC'
            WHEN LOWER(location) ~ 'philadelphia|pittsburgh|allentown|erie' THEN 'PA'
            WHEN LOWER(location) ~ 'phoenix|scottsdale|tempe|mesa|tucson|chandler' THEN 'AZ'
            WHEN LOWER(location) ~ 'detroit|ann arbor|grand rapids|lansing' THEN 'MI'
            WHEN LOWER(location) ~ 'minneapolis|st\. paul|bloomington|rochester' THEN 'MN'
            WHEN LOWER(location) ~ 'columbus|cleveland|cincinnati|toledo|dayton' THEN 'OH'
            WHEN LOWER(location) ~ 'nashville|memphis|knoxville|chattanooga' THEN 'TN'
            WHEN LOWER(location) ~ 'washington, d\.c\.|washington dc|dc|arlington|mclean|reston|tysons|alexandria' THEN 'DC'
            WHEN LOWER(location) ~ 'baltimore|bethesda|rockville|silver spring|annapolis' THEN 'MD'
            WHEN LOWER(location) ~ 'st\. louis|kansas city|springfield|columbia' THEN 'MO'
            WHEN LOWER(location) ~ 'indianapolis|fort wayne|evansville|south bend' THEN 'IN'
            WHEN LOWER(location) ~ 'salt lake city|lehi|provo|orem' THEN 'UT'
            WHEN LOWER(location) ~ 'richmond|norfolk|virginia beach|newport news' THEN 'VA'
            WHEN LOWER(location) ~ 'portland|eugene|salem|gresham' THEN 'OR'
            ELSE state
        END
        WHERE (state IS NULL OR state = '' OR LOWER(state) IN ('null','n/a','none','unknown'))
          AND location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none','unknown')
    """)
    print(f" -> Inferred recruiter states from cities for {cursor.rowcount:,} records in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # FINAL: STRICT VACUUM FULL & SIZE VERIFICATION
    # =========================================================================
    print("\n[Final] Executing VACUUM FULL to enforce hard <400 MB Rule 7 limit...")
    t0 = time.time()
    conn.autocommit = True
    cursor.execute("VACUUM FULL recruiters")
    cursor.execute("VACUUM FULL companies")
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f" -> VACUUM FULL complete in {time.time()-t0:.1f}s. Final DB Size: {db_size:.2f} MB / 400 MB")
    print("=" * 80)
    print(f"MASS FREE ENRICHMENT PHASE 2 COMPLETE IN {time.time()-start_total:.1f}s!")
    print("=" * 80)

if __name__ == '__main__':
    run_phase2_enrichment()
