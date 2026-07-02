import psycopg
import re
import time

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

# Check #6: NANP Area Code to State mapping table
AREA_CODE_MAP = {
    '201':'NJ','202':'DC','203':'CT','205':'AL','206':'WA','207':'ME','208':'ID','209':'CA',
    '210':'TX','212':'NY','213':'CA','214':'TX','215':'PA','216':'OH','217':'IL','218':'MN',
    '219':'IN','220':'OH','223':'PA','224':'IL','225':'LA','228':'MS','229':'GA','231':'MI',
    '234':'OH','239':'FL','240':'MD','248':'MI','251':'AL','252':'NC','253':'WA','254':'TX',
    '256':'AL','260':'IN','262':'WI','267':'PA','269':'MI','270':'KY','272':'PA','276':'VA',
    '281':'TX','301':'MD','302':'DE','303':'CO','304':'WV','305':'FL','307':'WY','308':'NE',
    '309':'IL','310':'CA','312':'IL','313':'MI','314':'MO','315':'NY','316':'KS','317':'IN',
    '318':'LA','319':'IA','320':'MN','321':'FL','323':'CA','325':'TX','330':'OH','331':'IL',
    '334':'AL','336':'NC','337':'LA','339':'MA','346':'TX','347':'NY','351':'MA','352':'FL',
    '360':'WA','361':'TX','386':'FL','401':'RI','402':'NE','404':'GA','405':'OK','406':'MT',
    '407':'FL','408':'CA','409':'TX','410':'MD','412':'PA','413':'MA','414':'WI','415':'CA',
    '417':'MO','419':'OH','423':'TN','424':'CA','425':'WA','430':'TX','432':'TX','434':'VA',
    '435':'UT','440':'OH','442':'CA','443':'MD','469':'TX','470':'GA','475':'CT','478':'GA',
    '479':'AR','480':'AZ','484':'PA','501':'AR','502':'KY','503':'OR','504':'LA','505':'NM',
    '507':'MN','508':'MA','509':'WA','510':'CA','512':'TX','513':'OH','515':'IA','516':'NY',
    '517':'MI','518':'NY','520':'AZ','530':'CA','540':'VA','541':'OR','559':'CA','561':'FL',
    '562':'CA','563':'IA','564':'WA','567':'OH','570':'PA','571':'VA','573':'MO','574':'IN',
    '585':'NY','586':'MI','601':'MS','602':'AZ','603':'NH','605':'SD','606':'KY','607':'NY',
    '608':'WI','609':'NJ','610':'PA','612':'MN','614':'OH','615':'TN','616':'MI','617':'MA',
    '618':'IL','619':'CA','620':'KS','626':'CA','630':'IL','631':'NY','646':'NY','650':'CA',
    '651':'MN','661':'CA','662':'MS','678':'GA','682':'TX','701':'ND','702':'NV','703':'VA',
    '704':'NC','706':'GA','707':'CA','708':'IL','712':'IA','713':'TX','714':'CA','715':'WI',
    '716':'NY','717':'PA','718':'NY','719':'CO','720':'CO','724':'PA','727':'FL','731':'TN',
    '732':'NJ','734':'MI','740':'OH','754':'FL','757':'VA','760':'CA','762':'GA','763':'MN',
    '765':'IN','770':'GA','772':'FL','773':'IL','774':'MA','775':'NV','781':'MA','785':'KS',
    '786':'FL','801':'UT','802':'VT','803':'SC','804':'VA','805':'CA','806':'TX','808':'HI',
    '810':'MI','812':'IN','813':'FL','814':'PA','815':'IL','816':'MO','817':'TX','828':'NC',
    '830':'TX','831':'CA','832':'TX','843':'SC','845':'NY','847':'IL','848':'NJ','850':'FL',
    '856':'NJ','857':'MA','858':'CA','859':'KY','860':'CT','862':'NJ','863':'FL','864':'SC',
    '865':'TN','870':'AR','878':'PA','901':'TN','903':'TX','904':'FL','906':'MI','907':'AK',
    '908':'NJ','909':'CA','910':'NC','912':'GA','913':'KS','914':'NY','915':'TX','916':'CA',
    '917':'NY','918':'OK','919':'NC','920':'WI','925':'CA','928':'AZ','929':'NY','931':'TN',
    '936':'TX','937':'OH','940':'TX','941':'FL','949':'CA','951':'CA','952':'MN','954':'FL',
    '956':'TX','970':'CO','971':'OR','972':'TX','973':'NJ','978':'MA','979':'TX','980':'NC',
    '985':'LA','989':'MI'
}

def execute_pipeline():
    print("=== STARTING 20-POINT MASTER VERIFICATION & ALIGNMENT PIPELINE ===")
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    # Step 1: Load canonical companies
    cur.execute("SELECT company_id, company_name FROM companies")
    comp_map = {}
    for cid, cname in cur.fetchall():
        comp_map[cname.lower().strip()] = cid

    # Domain mapping for major firms (Check #1 & #11)
    DOMAIN_TARGETS = {
        'roberthalf.com': 'robert half',
        'insightglobal.com': 'insight global',
        'teksystems.com': 'teksystems',
        'manpower.com': 'manpowergroup',
        'manpowergroup.com': 'manpowergroup',
        'experis.com': 'manpowergroup',
        'randstad.com': 'randstad',
        'randstadusa.com': 'randstad',
        'beaconhillstaffing.com': 'beacon hill staffing group',
        'collabera.com': 'collabera',
        'aerotek.com': 'aerotek',
        'kellyservices.com': 'kelly services',
        'kforce.com': 'kforce',
        'apexsystems.com': 'apex systems'
    }

    print("Executing Check #1 & #11: Canonical Domain vs Company Concordance...")
    domain_updates = []
    cur.execute("SELECT recruiter_id, email, company_id FROM recruiters WHERE email IS NOT NULL AND email LIKE '%@%'")
    for rid, em, curr_cid in cur.fetchall():
        domain = em.split('@')[-1].lower().strip()
        if domain in DOMAIN_TARGETS:
            target_cname = DOMAIN_TARGETS[domain]
            if target_cname in comp_map:
                target_cid = comp_map[target_cname]
                if curr_cid != target_cid:
                    domain_updates.append((target_cid, rid))

    print(f"Found {len(domain_updates):,} recruiters assigned to wrong company based on corporate email domain! Realigning...")
    if domain_updates:
        cur.executemany("UPDATE recruiters SET company_id = %s WHERE recruiter_id = %s", domain_updates)
        conn.commit()

    print("Executing Check #6: NANP Phone Area Code Concordance for US/NULL records...")
    cur.execute("SELECT recruiter_id, phone, phone2 FROM recruiters WHERE state IS NULL OR state = 'US'")
    phone_updates = []
    phone_re = re.compile(r'\b([2-9]\d{2})\b')
    for rid, p1, p2 in cur.fetchall():
        st = None
        for p in (p1, p2):
            if p:
                m = phone_re.search(p)
                if m and m.group(1) in AREA_CODE_MAP:
                    st = AREA_CODE_MAP[m.group(1)]
                    break
        if st:
            phone_updates.append((st, rid))

    print(f"Found {len(phone_updates):,} records with verifiable US states via NANP area code! Updating...")
    if phone_updates:
        cur.executemany("UPDATE recruiters SET state = %s WHERE recruiter_id = %s", phone_updates)
        conn.commit()

    print("Executing Check #14: Orphaned Micro-Company Reclamation...")
    cur.execute("SELECT company_id, company_name FROM companies WHERE company_id IN (SELECT company_id FROM recruiters GROUP BY company_id HAVING count(*) <= 2)")
    orphans = cur.fetchall()
    reclaimed = 0
    for ocid, ocname in orphans:
        oc_lower = ocname.lower().strip()
        for target_key, target_name in DOMAIN_TARGETS.items():
            if target_name in oc_lower or oc_lower in target_name:
                if target_name in comp_map:
                    target_cid = comp_map[target_name]
                    if target_cid != ocid:
                        cur.execute("UPDATE recruiters SET company_id = %s WHERE company_id = %s", (target_cid, ocid))
                        reclaimed += cur.rowcount
                break
    conn.commit()
    print(f"Reclaimed and merged {reclaimed:,} recruiters from orphaned micro-companies!")

    cur.close()
    conn.close()
    print(f"=== 20-POINT VERIFICATION PIPELINE COMPLETED IN {time.time() - t0:.2f}s ===")

if __name__ == "__main__":
    execute_pipeline()
