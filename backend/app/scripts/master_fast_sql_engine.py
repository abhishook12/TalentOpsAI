import time
import psycopg

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

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

def execute_fast_sql():
    print("=== STARTING FAST SERVER-SIDE SQL EXECUTION ENGINE (prepare=False) ===", flush=True)
    t0 = time.time()
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT company_id, company_name FROM companies", prepare=False)
    comp_map = {cname.lower().strip(): cid for cid, cname in cur.fetchall()}

    print("\n[Point #1 & #11] Executing Server-Side Bulk Domain Alignment...", flush=True)
    total_aligned = 0
    for dom, target_name in DOMAIN_MAP.items():
        if target_name in comp_map:
            cid = comp_map[target_name]
            cur.execute("UPDATE recruiters SET company_id = %s WHERE email LIKE %s AND company_id != %s", (cid, f"%@{dom}", cid), prepare=False)
            if cur.rowcount > 0:
                print(f" -> Aligned {cur.rowcount:,} recruiters for @{dom} -> {target_name.title()}", flush=True)
                total_aligned += cur.rowcount
    conn.commit()
    print(f"Total domain misalignments corrected: {total_aligned:,}", flush=True)

    print("\n[Point #6] Executing Server-Side NANP Area Code Alignment...", flush=True)
    total_phone = 0
    for ac, st in AREA_CODE_MAP.items():
        cur.execute("UPDATE recruiters SET state = %s WHERE (phone LIKE %s OR phone2 LIKE %s) AND (state IS NULL OR state = 'US')", (st, f"%{ac}%", f"%{ac}%"), prepare=False)
        if cur.rowcount > 0:
            total_phone += cur.rowcount
    conn.commit()
    print(f"Total NANP phone state corrections: {total_phone:,}", flush=True)

    print("\n=== FINAL TOP 15 COMPANIES ===", flush=True)
    cur.execute("SELECT c.company_name, count(*) FROM recruiters r JOIN companies c ON r.company_id = c.company_id GROUP BY c.company_name ORDER BY count DESC LIMIT 15", prepare=False)
    for cname, count in cur.fetchall():
        print(f"{cname:30}: {count:,}", flush=True)

    cur.close()
    conn.close()
    print(f"\n=== FAST SQL ENGINE COMPLETED IN {time.time() - t0:.2f}s ===", flush=True)

if __name__ == "__main__":
    execute_fast_sql()
