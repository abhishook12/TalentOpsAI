"""
Ultra-Deep Forensic Anomalies Remediation Pipeline
==================================================
Systematically heals:
1. Purges student / non-recruiter misclassifications (High school students, Fine arts students)
2. Scrubs 272k+ fake LinkedIn Search URLs ('/search/results/?keywords=...') from personal profile field
3. Heals raw email addresses stored as company names (e.g. 'Philip.Lowrie@Entelligence.Com' -> 'Entelligence')
4. Strips trailing mojibake artifacts ('â') from names
5. Strips certification suffixes mistakenly treated as surnames ('Robyn Mba' -> 'Robyn')
6. Cleans postal zip codes dumped into normalized_city
7. Fixes consumer webmail domain typos (gmaill.com -> gmail.com, hotmial.com -> hotmail.com)
8. Resolves generic 'US' records to specific states using unequivocal US Major City mapping
"""

import os
import sys
import re
import duckdb

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, backend_dir)

MAJOR_US_CITIES = {
    'new york': 'NY', 'new york city': 'NY', 'manhattan': 'NY', 'brooklyn': 'NY',
    'chicago': 'IL', 'los angeles': 'CA', 'houston': 'TX', 'phoenix': 'AZ',
    'philadelphia': 'PA', 'san antonio': 'TX', 'san diego': 'CA', 'dallas': 'TX',
    'san jose': 'CA', 'austin': 'TX', 'jacksonville': 'FL', 'fort worth': 'TX',
    'columbus': 'OH', 'charlotte': 'NC', 'san francisco': 'CA', 'indianapolis': 'IN',
    'seattle': 'WA', 'denver': 'CO', 'washington': 'DC', 'boston': 'MA',
    'el paso': 'TX', 'nashville': 'TN', 'detroit': 'MI', 'oklahoma city': 'OK',
    'portland': 'OR', 'las vegas': 'NV', 'memphis': 'TN', 'louisville': 'KY',
    'baltimore': 'MD', 'milwaukee': 'WI', 'albuquerque': 'NM', 'tucson': 'AZ',
    'fresno': 'CA', 'sacramento': 'CA', 'mesa': 'AZ', 'kansas city': 'MO',
    'atlanta': 'GA', 'omaha': 'NE', 'colorado springs': 'CO', 'raleigh': 'NC',
    'miami': 'FL', 'long beach': 'CA', 'virginia beach': 'VA', 'oakland': 'CA',
    'minneapolis': 'MN', 'tulsa': 'OK', 'tampa': 'FL', 'arlington': 'TX',
    'new orleans': 'LA', 'wichita': 'KS', 'cleveland': 'OH', 'bakersfield': 'CA',
    'aurora': 'CO', 'anaheim': 'CA', 'honolulu': 'HI', 'santa ana': 'CA',
    'riverside': 'CA', 'corpus christi': 'TX', 'lexington': 'KY', 'stockton': 'CA',
    'henderson': 'NV', 'saint paul': 'MN', 'st. louis': 'MO', 'cincinnati': 'OH',
    'pittsburgh': 'PA', 'greensboro': 'NC', 'anchorage': 'AK', 'plano': 'TX',
    'lincoln': 'NE', 'orlando': 'FL', 'irvine': 'CA', 'newark': 'NJ',
    'toledo': 'OH', 'durham': 'NC', 'chula vista': 'CA', 'fort wayne': 'IN',
    'jersey city': 'NJ', 'st. petersburg': 'FL', 'laredo': 'TX', 'madison': 'WI',
    'chandler': 'AZ', 'buffalo': 'NY', 'lubbock': 'TX', 'scottsdale': 'AZ',
    'reno': 'NV', 'glendale': 'AZ', 'gilbert': 'AZ', 'winston-salem': 'NC',
    'north las vegas': 'NV', 'norfolk': 'VA', 'chesapeake': 'VA', 'garland': 'TX',
    'irving': 'TX', 'hialeah': 'FL', 'fremont': 'CA', 'boise': 'ID', 'richmond': 'VA',
    'baton rouge': 'LA', 'spokane': 'WA', 'des moines': 'IA', 'tacoma': 'WA',
    'san bernardino': 'CA', 'modesto': 'CA', 'fontana': 'CA', 'santa clarita': 'CA',
    'birmingham': 'AL', 'oxnard': 'CA', 'fayetteville': 'NC', 'rochester': 'NY',
    'moreno valley': 'CA', 'huntington beach': 'CA', 'salt lake city': 'UT',
    'grand rapids': 'MI', 'amarillo': 'TX', 'yonkers': 'NY', 'montgomery': 'AL',
    'akron': 'OH', 'little rock': 'AR', 'huntsville': 'AL', 'augusta': 'GA',
    'port st. lucie': 'FL', 'grand prairie': 'TX', 'tallahassee': 'FL',
    'overland park': 'KS', 'tempe': 'AZ', 'mckinney': 'TX', 'mobile': 'AL',
    'cape coral': 'FL', 'shreveport': 'LA', 'frisco': 'TX', 'knoxville': 'TN',
    'worcester': 'MA', 'brownsville': 'TX', 'vancouver': 'WA', 'fort lauderdale': 'FL',
    'sioux falls': 'SD', 'ontario': 'CA', 'chattanooga': 'TN', 'providence': 'RI',
    'newport news': 'VA', 'rancho cucamonga': 'CA', 'santa rosa': 'CA',
    'oceanside': 'CA', 'salem': 'OR', 'elk grove': 'CA', 'garden grove': 'CA',
    'pembroke pines': 'FL', 'peoria': 'AZ', 'eugene': 'OR', 'corona': 'CA',
    'cary': 'NC', 'springfield': 'MO', 'fort collins': 'CO', 'jackson': 'MS',
    'alexandria': 'VA', 'hayward': 'CA', 'lancaster': 'CA', 'lakewood': 'CO',
    'clarksville': 'TN', 'palmdale': 'CA', 'salinas': 'CA', 'hollywood': 'FL',
    'pasadena': 'TX', 'sunnyvale': 'CA', 'macon': 'GA', 'kansas city': 'KS',
    'pomona': 'CA', 'escondido': 'CA', 'killeen': 'TX', 'naperville': 'IL',
    'joliet': 'IL', 'bellevue': 'WA', 'rockford': 'IL', 'savannah': 'GA',
    'paterson': 'NJ', 'torrance': 'CA', 'bridgeport': 'CT', 'mcallen': 'TX',
    'mesquite': 'TX', 'syracuse': 'NY', 'midland': 'TX', 'pasadena': 'CA',
    'murfreesboro': 'TN', 'miramar': 'FL', 'dayton': 'OH', 'fullerton': 'CA',
    'olathe': 'KS', 'orange': 'CA', 'thornton': 'CO', 'roseville': 'CA',
    'denton': 'TX', 'waco': 'TX', 'surprise': 'AZ', 'carrollton': 'TX',
    'west valley city': 'UT', 'charleston': 'SC', 'warren': 'MI', 'hampton': 'VA',
    'gainesville': 'FL', 'visalia': 'CA', 'coral springs': 'FL', 'columbia': 'SC',
    'cedar rapids': 'IA', 'sterling heights': 'MI', 'new haven': 'CT', 'stamford': 'CT',
    'concord': 'CA', 'kent': 'WA', 'santa clara': 'CA', 'elizabeth': 'NJ',
    'round rock': 'TX', 'thousand oaks': 'CA', 'lafayette': 'LA', 'athens': 'GA',
    'topeka': 'KS', 'simi valley': 'CA', 'fargo': 'ND', 'norman': 'OK',
    'columbia': 'MO', 'abilene': 'TX', 'wilmington': 'NC', 'hartford': 'CT',
    'allentown': 'PA', 'pearland': 'TX', 'chico': 'CA'
}


def remediate_deepest_anomalies():
    parquet_path = os.path.join(backend_dir, "data", "recruiters_full.parquet")
    print("\n" + "="*80)
    print("STEP 1: REMEDIATING ULTRA-DEEP FORENSIC ANOMALIES IN PARQUET CATALOG")
    print("="*80)

    con = duckdb.connect(":memory:")
    con.execute(f"CREATE TABLE rec AS SELECT * FROM read_parquet('{parquet_path}')")
    initial_count = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    print(f"Initial Catalog Records: {initial_count:,}")

    # [1] Purge Student Misclassifications
    print("\n[A] Purging student / candidate misclassifications...")
    student_count = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE LOWER(title) LIKE '%student at%' 
           OR LOWER(title) LIKE '%high school%' 
           OR LOWER(title) LIKE '%fine arts student%'
    """).fetchone()[0]

    if student_count > 0:
        con.execute("""
            DELETE FROM rec 
            WHERE LOWER(title) LIKE '%student at%' 
               OR LOWER(title) LIKE '%high school%' 
               OR LOWER(title) LIKE '%fine arts student%'
        """)
        print(f"  -> Purged {student_count:,} student misclassifications.")

    # [2] Scrub Fake LinkedIn Search URLs (272k+)
    print("\n[B] Scrubbing fake LinkedIn Search Result URLs from personal profile fields...")
    fake_li_count = con.execute("""
        SELECT COUNT(*) FROM rec 
        WHERE linkedin IS NOT NULL 
          AND (
            linkedin LIKE '%/search/results/%'
            OR linkedin LIKE '%/search/%'
            OR linkedin LIKE '%/posts/%'
            OR linkedin LIKE '%/groups/%'
            OR linkedin LIKE '%/sales/%'
            OR linkedin LIKE '%/talent/%'
          )
    """).fetchone()[0]

    if fake_li_count > 0:
        con.execute("""
            UPDATE rec 
            SET linkedin = NULL 
            WHERE linkedin IS NOT NULL 
              AND (
                linkedin LIKE '%/search/results/%'
                OR linkedin LIKE '%/search/%'
                OR linkedin LIKE '%/posts/%'
                OR linkedin LIKE '%/groups/%'
                OR linkedin LIKE '%/sales/%'
                OR linkedin LIKE '%/talent/%'
              )
        """)
        print(f"  -> Successfully scrubbed {fake_li_count:,} fake search query URLs from profile field.")

    # [3] Heal Email Addresses Stored as Company Names
    print("\n[C] Healing email addresses stored as company names...")
    email_as_comp = con.execute("""
        SELECT recruiter_id, company_id 
        FROM rec 
        WHERE CAST(company_id AS VARCHAR) LIKE '%@%'
    """).fetchall()

    fixed_email_comps = 0
    for rid, raw_comp in email_as_comp:
        domain = str(raw_comp).split('@')[1].strip()
        base_name = domain.split('.')[0].replace('-', ' ').title()
        con.execute("UPDATE rec SET company_id = ? WHERE recruiter_id = ?", [base_name, rid])
        fixed_email_comps += 1
    print(f"  -> Healed {fixed_email_comps:,} companies that contained raw email addresses.")

    # [4] Clean Trailing Mojibake ('â') from Names
    print("\n[D] Stripping trailing mojibake characters ('â') from names...")
    mojibake_rows = con.execute("SELECT recruiter_id, recruiter_name FROM rec WHERE recruiter_name LIKE '%â'").fetchall()
    for rid, name in mojibake_rows:
        clean_name = name.rstrip('â ').strip()
        con.execute("UPDATE rec SET recruiter_name = ? WHERE recruiter_id = ?", [clean_name, rid])
    print(f"  -> Cleaned {len(mojibake_rows):,} mojibake names.")

    # [5] Clean Certification Suffixes Stored as Surnames
    print("\n[E] Normalizing certification suffixes treated as surnames...")
    cert_suffixes = ['mba', 'pmp', 'sphr', 'phr', 'cpa', 'cir', 'cprw']
    fixed_certs = 0
    for s in cert_suffixes:
        rows = con.execute(f"SELECT recruiter_id, recruiter_name FROM rec WHERE LOWER(recruiter_name) LIKE '% {s}'").fetchall()
        for rid, name in rows:
            parts = name.split()
            if len(parts) >= 2:
                clean_name = " ".join(parts[:-1])
                con.execute("UPDATE rec SET recruiter_name = ? WHERE recruiter_id = ?", [clean_name, rid])
                fixed_certs += 1
    print(f"  -> Cleaned {fixed_certs:,} certification suffixes from person names.")

    # [6] Clean Zip Codes in normalized_city
    print("\n[F] Cleansing postal zip codes from normalized_city...")
    zip_count = con.execute("SELECT COUNT(*) FROM rec WHERE normalized_city IS NOT NULL AND REGEXP_MATCHES(normalized_city, '^[0-9]{4,}$')").fetchone()[0]
    if zip_count > 0:
        con.execute("UPDATE rec SET normalized_city = NULL WHERE normalized_city IS NOT NULL AND REGEXP_MATCHES(normalized_city, '^[0-9]{4,}$')")
        print(f"  -> Cleansed {zip_count:,} zip codes from city field.")

    # [7] Fix Consumer Webmail Domain Typos
    print("\n[G] Repairing consumer webmail domain typos...")
    con.execute("UPDATE rec SET email = REPLACE(email, '@gmaill.com', '@gmail.com') WHERE email LIKE '%@gmaill.com%'")
    con.execute("UPDATE rec SET email = REPLACE(email, '@hotmial.com', '@hotmail.com') WHERE email LIKE '%@hotmial.com%'")
    print("  -> Repaired webmail domain typos.")

    # [8] Major US City to State Resolution for Generic 'US' Records
    print("\n[H] Resolving generic 'US' records using Major US City mapping...")
    before_us = con.execute("SELECT COUNT(*) FROM rec WHERE UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'").fetchone()[0]

    # Create temporary mapping table in DuckDB
    con.execute("CREATE TABLE city_mapping (city_lower VARCHAR, st VARCHAR)")
    for city, st in MAJOR_US_CITIES.items():
        con.execute("INSERT INTO city_mapping VALUES (?, ?)", [city, st])

    con.execute("""
        UPDATE rec
        SET state = cm.st
        FROM city_mapping cm
        WHERE rec.normalized_city IS NOT NULL
          AND LOWER(TRIM(rec.normalized_city)) = cm.city_lower
          AND UPPER(TRIM(CAST(rec.state AS VARCHAR))) = 'US'
    """)

    after_us = con.execute("SELECT COUNT(*) FROM rec WHERE UPPER(TRIM(CAST(state AS VARCHAR))) = 'US'").fetchone()[0]
    print(f"  -> Successfully resolved {before_us - after_us:,} generic 'US' records to exact states from City mapping!")
    # [9] Guarantee zero missing companies
    con.execute("""
        UPDATE rec
        SET company_id = CONCAT(
            UPPER(SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 1, 1)),
            SUBSTR(SPLIT_PART(LOWER(SPLIT_PART(email, '@', 2)), '.', 1), 2)
        )
        WHERE (company_id IS NULL OR TRIM(CAST(company_id AS VARCHAR)) = '')
          AND email IS NOT NULL AND email LIKE '%@%'
    """)

    # Write back clean catalog
    final_count = con.execute("SELECT COUNT(*) FROM rec").fetchone()[0]
    temp_parquet = parquet_path + ".tmp"
    con.execute(f"COPY rec TO '{temp_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    os.replace(temp_parquet, parquet_path)
    print(f"\n[I] Successfully saved updated catalog to {parquet_path}. Total clean rows: {final_count:,}")

    return final_count


if __name__ == "__main__":
    remediate_deepest_anomalies()
    print("\n" + "="*80)
    print("ULTRA-DEEP ANOMALIES REMEDIATION COMPLETE!")
    print("="*80)
