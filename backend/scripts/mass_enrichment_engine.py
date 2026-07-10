import os
import time
import psycopg
from dotenv import load_dotenv

def run_mass_enrichment():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SET statement_timeout = 0;")

    print("=" * 80)
    print("MASS FREE ENRICHMENT ENGINE v4 (BATCHED ULTRA FAST)")
    print("=" * 80)
    start_total = time.time()

    def update_batched(query, params, batch_size=25000, desc=""):
        total_updated = 0
        while True:
            # We use ctid / primary key subquery limit for fast updates
            batched_query = f"""
                WITH batch AS (
                    {query}
                    LIMIT {batch_size}
                )
                UPDATE recruiters r
                SET {params['set_clause']}
                FROM batch
                WHERE r.recruiter_id = batch.recruiter_id
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
    # ITEM 1: Parse Specialization from Job Title (Fast ILIKE + Chunked General)
    # =========================================================================
    print("\n[Item 1/8] Parsing Specialization from Job Title...")
    t0 = time.time()
    
    spec_keywords = [
        ('Information Technology', ['%software%', '%developer%', '%engineer%', '%devops%', '%cloud%', '%data%', '%cyber%', '%sap%', '%java%', '%python%', '%.net%', '%frontend%', '%backend%', '%full stack%', '%fullstack%', '%tech%', '%infrastructure%', '%network%', '%systems%', '%database%', '%ai %', '%machine learning%', '%security%', '%helpdesk%', '%desktop support%', '%qa%', '%quality assurance%', '%scrum%', '%agile%', '%product manager%', '%ux%', '%ui%']),
        ('Healthcare', ['%healthcare%', '%medical%', '%nurse%', '%nursing%', '%clinical%', '%pharma%', '%biotech%', '%health %', '%dental%', '%physician%', '%therapist%', '%hospital%', '%patient%']),
        ('Finance & Accounting', ['%finance%', '%financial%', '%accounting%', '%accountant%', '%cpa%', '%audit%', '%tax%', '%banking%', '%investment%', '%mortgage%', '%loan%', '%treasury%', '%controller%']),
        ('Engineering', ['%mechanical%', '%electrical%', '%civil%', '%structural%', '%manufacturing%', '%industrial%', '%chemical engineer%', '%aerospace%']),
        ('Sales & Marketing', ['%sales%', '%marketing%', '%business development%', '%account executive%', '%sdr%', '%bdr%', '%demand gen%', '%brand%', '%advertising%', '%digital marketing%', '%seo%', '%content%']),
        ('Human Resources', ['%human resources%', '%hr%', '%talent%', '%recruiting%', '%recruiter%', '%staffing%', '%workforce%', '%people operations%', '%compensation%', '%benefits%', '%payroll%', '%hris%']),
        ('Legal', ['%legal%', '%attorney%', '%lawyer%', '%paralegal%', '%compliance%', '%regulatory%', '%counsel%', '%litigation%']),
        ('Operations & Logistics', ['%operations%', '%logistics%', '%supply chain%', '%warehouse%', '%procurement%', '%transportation%', '%fleet%', '%distribution%', '%inventory%']),
        ('Construction & Trades', ['%construction%', '%plumber%', '%electrician%', '%hvac%', '%carpenter%', '%welder%', '%mason%', '%roofing%']),
        ('Creative & Design', ['%design%', '%graphic%', '%creative%', '%photographer%', '%video%', '%animation%', '%art director%', '%copywriter%']),
        ('Education', ['%education%', '%teacher%', '%professor%', '%instructor%', '%training%', '%curriculum%', '%academic%', '%tutor%']),
        ('Executive', ['%executive%', '%ceo%', '%cfo%', '%cto%', '%coo%', '%cio%', '%vp%', '%vice president%', '%director%', '%chief%', '%svp%', '%evp%', '%managing director%', '%partner%', '%principal%']),
        ('Customer Service', ['%customer service%', '%customer support%', '%call center%', '%client services%', '%support specialist%']),
        ('Project Management', ['%project manager%', '%program manager%', '%pmo%', '%project coordinator%', '%scrum master%']),
        ('Administrative', ['%administrative%', '%office manager%', '%executive assistant%', '%receptionist%', '%coordinator%', '%clerk%'])
    ]

    total_specs = 0
    for category, patterns in spec_keywords:
        cursor.execute("""
            UPDATE recruiters
            SET specialization = %s
            WHERE (specialization IS NULL OR specialization = '' OR LOWER(specialization) IN ('null','n/a','none','unknown'))
              AND title ILIKE ANY(%s)
        """, (category, patterns))
        total_specs += cursor.rowcount
    conn.commit()

    # Chunked update for General Staffing
    total_specs += update_batched(
        query="SELECT recruiter_id FROM recruiters WHERE (specialization IS NULL OR specialization = '' OR LOWER(specialization) IN ('null','n/a','none','unknown')) AND title IS NOT NULL AND title != ''",
        params={'set_clause': "specialization = 'General Staffing'"},
        batch_size=25000,
        desc="General Staffing chunked assignments"
    )
    print(f" -> Parsed specialization total: {total_specs:,} in {time.time()-t0:.1f}s.")

    # =========================================================================
    # ITEM 2: Infer Company Website from recruiter emails
    # =========================================================================
    print("\n[Item 2/8] Inferring Company Website from recruiter emails...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies c
        SET website = sub.domain
        FROM (
            SELECT DISTINCT ON (r.company_id) r.company_id, SPLIT_PART(r.email, '@', 2) as domain
            FROM recruiters r
            JOIN companies c2 ON r.company_id = c2.company_id
            WHERE (c2.website IS NULL OR c2.website = '' OR LOWER(c2.website) IN ('null','n/a'))
              AND r.email LIKE '%%@%%.%%'
              AND r.email NOT LIKE 'scrubbed-%%'
            ORDER BY r.company_id
        ) sub
        WHERE c.company_id = sub.company_id
          AND (c.website IS NULL OR c.website = '' OR LOWER(c.website) IN ('null','n/a'))
    """)
    print(f" -> Inferred website for {cursor.rowcount:,} companies in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # ITEM 3: Copy City/Location from Company HQ (Chunked)
    # =========================================================================
    print("\n[Item 3/8] Copying City/Location from Company HQ...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT r.recruiter_id, c.location as new_loc
            FROM recruiters r JOIN companies c ON r.company_id = c.company_id
            WHERE (r.location IS NULL OR r.location = '' OR LOWER(r.location) IN ('null','n/a','none','unknown'))
              AND c.location IS NOT NULL AND c.location != '' AND LOWER(c.location) NOT IN ('null','n/a','none')
        """,
        params={'set_clause': "location = batch.new_loc"},
        batch_size=25000,
        desc="Copied location from HQ"
    )

    # =========================================================================
    # ITEM 4: Infer State from Company State (Chunked)
    # =========================================================================
    print("\n[Item 4/8] Inferring State from Company State...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT r.recruiter_id, c.state as new_state
            FROM recruiters r JOIN companies c ON r.company_id = c.company_id
            WHERE (r.state IS NULL OR r.state = '' OR LOWER(r.state) IN ('null','n/a','none','unknown'))
              AND c.state IS NOT NULL AND c.state != '' AND LOWER(c.state) NOT IN ('null','n/a','none')
        """,
        params={'set_clause': "state = batch.new_state"},
        batch_size=25000,
        desc="Inferred state from company"
    )

    # =========================================================================
    # ITEM 5: Detect Email Pattern
    # =========================================================================
    print("\n[Item 5/8] Detecting Email Patterns for companies...")
    t0 = time.time()
    cursor.execute("""
        UPDATE companies c
        SET email_pattern = sub.pattern
        FROM (
            SELECT company_id,
                CASE
                    WHEN SUM(CASE WHEN SPLIT_PART(email, '@', 1) LIKE '%%._%%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) >= 0.5 THEN '{first}.{last}'
                    WHEN SUM(CASE WHEN SPLIT_PART(email, '@', 1) LIKE '%%!_%%' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) >= 0.5 THEN '{first}_{last}'
                    ELSE '{first}{last}'
                END as pattern
            FROM recruiters
            WHERE email LIKE '%%@%%.%%' AND email NOT LIKE 'scrubbed-%%'
            GROUP BY company_id
            HAVING COUNT(*) >= 2
        ) sub
        WHERE c.company_id = sub.company_id
          AND (c.email_pattern IS NULL OR c.email_pattern = '' OR LOWER(c.email_pattern) IN ('null','n/a'))
    """)
    print(f" -> Detected email pattern for {cursor.rowcount:,} companies in {time.time()-t0:.1f}s.")
    conn.commit()

    # =========================================================================
    # ITEM 6: Auto-generate Tags (Chunked)
    # =========================================================================
    print("\n[Item 6/8] Auto-generating Tags...")
    t0 = time.time()
    update_batched(
        query="SELECT recruiter_id, specialization as new_tag FROM recruiters WHERE (tags IS NULL OR tags = '' OR LOWER(tags) IN ('null','n/a','none')) AND specialization IS NOT NULL AND specialization != '' AND LOWER(specialization) NOT IN ('null','n/a','none','unknown')",
        params={'set_clause': "tags = batch.new_tag"},
        batch_size=25000,
        desc="Recruiter tags from specialization"
    )

    cursor.execute("""
        UPDATE companies
        SET tags = industry
        WHERE (tags IS NULL OR tags = '' OR LOWER(tags) IN ('null','n/a','none'))
          AND industry IS NOT NULL AND industry != '' AND LOWER(industry) NOT IN ('null','n/a','none')
    """)
    print(f" -> Tagged {cursor.rowcount:,} companies from industry.")
    conn.commit()

    # =========================================================================
    # ITEM 7: Compute Trust Score (Chunked)
    # =========================================================================
    print("\n[Item 7/8] Computing Trust Score...")
    t0 = time.time()
    update_batched(
        query="""
            SELECT recruiter_id,
            LEAST(100, GREATEST(0,
                CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE 'scrubbed-%%' THEN 25 ELSE 0 END +
                CASE WHEN phone IS NOT NULL AND phone != '' THEN 15 ELSE 0 END +
                CASE WHEN linkedin IS NOT NULL AND linkedin != '' THEN 10 ELSE 0 END +
                CASE WHEN location IS NOT NULL AND location != '' AND LOWER(location) NOT IN ('null','n/a','none','unknown') THEN 10 ELSE 0 END +
                CASE WHEN state IS NOT NULL AND state != '' AND LOWER(state) NOT IN ('null','n/a','none','unknown') THEN 5 ELSE 0 END +
                CASE WHEN specialization IS NOT NULL AND specialization != '' AND LOWER(specialization) NOT IN ('null','n/a','none','unknown') THEN 10 ELSE 0 END +
                CASE WHEN title IS NOT NULL AND title != '' THEN 10 ELSE 0 END +
                CASE WHEN company_id IS NOT NULL THEN 15 ELSE 0 END
            )) as calc_score
            FROM recruiters
            WHERE trust_score IS NULL OR trust_score = 0
        """,
        params={'set_clause': "trust_score = batch.calc_score"},
        batch_size=25000,
        desc="Computed trust scores"
    )

    # =========================================================================
    # ITEM 8: Tag Data Source (Chunked)
    # =========================================================================
    print("\n[Item 8/8] Tagging Data Source for untagged rows...")
    t0 = time.time()
    update_batched(
        query="SELECT recruiter_id FROM recruiters WHERE data_source IS NULL OR data_source = '' OR LOWER(data_source) IN ('null','n/a','none')",
        params={'set_clause': "data_source = 'teams_extractor'"},
        batch_size=25000,
        desc="Tagged data_source as teams_extractor"
    )

    # =========================================================================
    # FINAL: VACUUM + SIZE CHECK
    # =========================================================================
    print("\n[Final] Optimizing database...")
    t0 = time.time()
    conn.autocommit = True
    cursor.execute("VACUUM recruiters")
    cursor.execute("VACUUM companies")
    cursor.execute("SELECT pg_database_size('postgres') / 1048576.0")
    db_size = cursor.fetchone()[0]
    print(f" -> VACUUM complete in {time.time()-t0:.1f}s. DB Size: {db_size:.2f} MB / 400 MB")
    print("=" * 80)
    print(f"MASS FREE ENRICHMENT v4 COMPLETE IN {time.time()-start_total:.1f}s!")
    print("=" * 80)

if __name__ == '__main__':
    run_mass_enrichment()
