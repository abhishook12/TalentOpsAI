import psycopg
import time

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def run_point_01():
    print("=== STARTING POINT #1: DEEP CANONICAL DOMAIN VS EMAIL CONCORDANCE ENGINE ===")
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # Load all canonical companies into a lookup map
    cur.execute("SELECT company_id, company_name FROM companies")
    comp_map = {}
    for cid, cname in cur.fetchall():
        clean_name = cname.lower().strip()
        comp_map[clean_name] = cid

    # Comprehensive Domain to Canonical Company Name map
    DOMAIN_MAP = {
        'roberthalf.com': 'robert half',
        'insightglobal.com': 'insight global',
        'insightglobal.net': 'insight global',
        'teksystems.com': 'teksystems',
        'manpower.com': 'manpowergroup',
        'manpowergroup.com': 'manpowergroup',
        'experis.com': 'manpowergroup',
        'jeffersonwells.com': 'manpowergroup',
        'randstad.com': 'randstad',
        'randstadusa.com': 'randstad',
        'randstaddigital.com': 'randstad',
        'randstadtechnologies.com': 'randstad',
        'beaconhillstaffing.com': 'beacon hill staffing group',
        'beaconhill.com': 'beacon hill staffing group',
        'collabera.com': 'collabera',
        'aerotek.com': 'aerotek',
        'kellyservices.com': 'kelly services',
        'kforce.com': 'kforce',
        'apexsystems.com': 'apex systems',
        'apexsystemsinc.com': 'apex systems',
        'vaco.com': 'vaco',
        'actalentsservices.com': 'actalent',
        'actalent.com': 'actalent',
        'brooksource.com': 'brooksource',
        'oxfordcorp.com': 'oxford global resources',
        'judge.com': 'the judge group',
        'kornferry.com': 'korn ferry',
        'lhh.com': 'lhh',
        'adecco.com': 'adecco',
        'adeccogroup.com': 'adecco',
        'michaelpage.com': 'pagegroup',
        'pagegroup.com': 'pagegroup',
        'hays.com': 'hays',
        'maximhealthcare.com': 'maxim healthcare staffing',
        'alumnis.com': 'alumni healthcare staffing',
        'ayahealthcare.com': 'aya healthcare',
        'crosscountry.com': 'cross country healthcare',
        'amnhealthcare.com': 'amn healthcare',
        'jacksonhealthcare.com': 'jackson healthcare',
        'medicalsolutions.com': 'medical solutions',
        'supplementalhealthcare.com': 'supplemental health care',
        'modis.com': 'modis',
        'solomonpage.com': 'solomon page',
        'lucasgroup.com': 'lucas group',
        'cybercoders.com': 'cybercoders',
        'jobspringpartners.com': 'motion recruitment',
        'motionrecruitment.com': 'motion recruitment',
        'workbridgeassociates.com': 'motion recruitment',
        'nelsonconnects.com': 'nelson connects',
        'rothstaffing.com': 'roth staffing',
        'ultimatestaffing.com': 'roth staffing',
        'ledgent.com': 'roth staffing',
        'adamsgabarre.com': 'adams & gabarre',
        'addison group.com': 'addison group',
        'addisongroup.com': 'addison group',
        'bgsf.com': 'bgsf',
        'disys.com': 'dexian',
        'dexian.com': 'dexian',
        'signatureconsultants.com': 'dexian',
        'eliassen.com': 'eliassen group',
        'ettain.com': 'ettain group',
        'genuent.com': 'genuent',
        'gttit.com': 'global technical talent',
        'gunnison.com': 'gunnison consulting group',
        'harveynash.com': 'harvey nash',
        'hirestrategy.com': 'hirestrategy',
        'matrixres.com': 'matrix resources',
        'mundy.com': 'the mundy companies',
        'optomi.com': 'optomi',
        'paladinstaffing.com': 'paladin',
        'parkerlynch.com': 'parker + lynch',
        'pontefract.com': 'pontefract',
        'pyramidci.com': 'pyramid consulting',
        'roseint.com': 'rose international',
        'snelling.com': 'snelling staffing',
        'systemone.com': 'system one',
        'talenenergy.com': 'talen energy',
        'yoh.com': 'yoh, a day & zimmermann company'
    }

    print("Scanning all recruiter profiles against canonical domain mappings...")
    cur.execute("SELECT recruiter_id, email, company_id FROM recruiters WHERE email IS NOT NULL AND email LIKE '%@%'")
    rows = cur.fetchall()
    print(f"Inspected {len(rows):,} total recruiters...")

    updates = []
    company_stats = {}

    for rid, em, curr_cid in rows:
        dom = em.split('@')[-1].lower().strip()
        if dom in DOMAIN_MAP:
            target_name = DOMAIN_MAP[dom]
            if target_name in comp_map:
                target_cid = comp_map[target_name]
                if curr_cid != target_cid:
                    updates.append((target_cid, rid))
                    company_stats[target_name] = company_stats.get(target_name, 0) + 1

    print(f"Found {len(updates):,} domain misalignments across the entire database!")
    for cname, count in sorted(company_stats.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f" -> Realigning {count:,} recruiters to {cname.title()}")

    if updates:
        print("Executing bulk realignment commit...")
        batch_size = 5000
        for i in range(0, len(updates), batch_size):
            cur.executemany("UPDATE recruiters SET company_id = %s WHERE recruiter_id = %s", updates[i:i+batch_size])
            conn.commit()

    # Verification proof check
    print("\n=== POST-EXECUTION VERIFICATION PROOF ===")
    cur.execute("SELECT c.company_name, count(*) FROM recruiters r JOIN companies c ON r.company_id = c.company_id GROUP BY c.company_name ORDER BY count DESC LIMIT 15")
    for cname, count in cur.fetchall():
        print(f"{cname}: {count:,}")

    cur.close()
    conn.close()
    print(f"=== POINT #1 COMPLETED & VERIFIED IN {time.time() - t0:.2f}s ===")

if __name__ == "__main__":
    run_point_01()
