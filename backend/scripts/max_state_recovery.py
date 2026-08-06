"""
Maximum free state recovery for US placeholder records.
Pass 1: Domain consensus (691K recoverable)
Pass 2: Company ID consensus
Pass 3: Phone area codes
Pass 4: Title/specialization cross-ref
"""
import pandas as pd
import duckdb
import re
import time

AREA_CODE_TO_STATE = {
    '201':'NJ','202':'DC','203':'CT','205':'AL','206':'WA','207':'ME','208':'ID',
    '209':'CA','210':'TX','212':'NY','213':'CA','214':'TX','215':'PA','216':'OH',
    '217':'IL','218':'MN','219':'IN','224':'IL','225':'LA','228':'MS','229':'GA',
    '231':'MI','234':'OH','239':'FL','240':'MD','248':'MI','251':'AL','252':'NC',
    '253':'WA','254':'TX','256':'AL','260':'IN','262':'WI','267':'PA','269':'MI',
    '270':'KY','272':'PA','276':'VA','281':'TX','301':'MD','302':'DE','303':'CO',
    '304':'WV','305':'FL','307':'WY','308':'NE','309':'IL','310':'CA','312':'IL',
    '313':'MI','314':'MO','315':'NY','316':'KS','317':'IN','318':'LA','319':'IA',
    '320':'MN','321':'FL','323':'CA','325':'TX','330':'OH','331':'IL','334':'AL',
    '336':'NC','337':'LA','339':'MA','346':'TX','347':'NY','351':'MA',
    '352':'FL','360':'WA','361':'TX','385':'UT','386':'FL','401':'RI','402':'NE',
    '404':'GA','405':'OK','406':'MT','407':'FL','408':'CA','409':'TX','410':'MD',
    '412':'PA','413':'MA','414':'WI','415':'CA','417':'MO','419':'OH','423':'TN',
    '424':'CA','425':'WA','430':'TX','432':'TX','434':'VA','435':'UT','440':'OH',
    '443':'MD','469':'TX','470':'GA','475':'CT','478':'GA','479':'AR','480':'AZ',
    '484':'PA','501':'AR','502':'KY','503':'OR','504':'LA','505':'NM','507':'MN',
    '508':'MA','509':'WA','510':'CA','512':'TX','513':'OH','515':'IA','516':'NY',
    '517':'MI','518':'NY','520':'AZ','530':'CA','531':'NE','539':'OK',
    '540':'VA','541':'OR','551':'NJ','559':'CA','561':'FL','562':'CA','563':'IA',
    '567':'OH','570':'PA','571':'VA','573':'MO','574':'IN','575':'NM','580':'OK',
    '585':'NY','586':'MI','601':'MS','602':'AZ','603':'NH','605':'SD','606':'KY',
    '607':'NY','608':'WI','609':'NJ','610':'PA','612':'MN','614':'OH','615':'TN',
    '616':'MI','617':'MA','618':'IL','619':'CA','620':'KS','623':'AZ','626':'CA',
    '629':'TN','630':'IL','631':'NY','636':'MO','641':'IA','646':'NY','650':'CA',
    '651':'MN','657':'CA','660':'MO','661':'CA','662':'MS','667':'MD','669':'CA',
    '678':'GA','681':'WV','682':'TX','689':'FL','701':'ND','702':'NV','703':'VA',
    '704':'NC','706':'GA','707':'CA','708':'IL','712':'IA','713':'TX','714':'CA',
    '715':'WI','716':'NY','717':'PA','718':'NY','719':'CO','720':'CO','724':'PA',
    '727':'FL','731':'TN','732':'NJ','734':'MI','737':'TX','740':'OH',
    '747':'CA','754':'FL','757':'VA','760':'CA','762':'GA','763':'MN','765':'IN',
    '769':'MS','770':'GA','772':'FL','773':'IL','774':'MA','775':'NV','779':'IL',
    '781':'MA','785':'KS','786':'FL','801':'UT','802':'VT','803':'SC',
    '804':'VA','805':'CA','806':'TX','808':'HI','810':'MI','812':'IN','813':'FL',
    '814':'PA','815':'IL','816':'MO','817':'TX','818':'CA','828':'NC','830':'TX',
    '831':'CA','832':'TX','843':'SC','845':'NY','847':'IL','848':'NJ',
    '850':'FL','854':'SC','856':'NJ','857':'MA','858':'CA','859':'KY','860':'CT',
    '862':'NJ','863':'FL','864':'SC','865':'TN','870':'AR','872':'IL',
    '901':'TN','903':'TX','904':'FL','906':'MI','907':'AK','908':'NJ','909':'CA',
    '910':'NC','912':'GA','913':'KS','914':'NY','915':'TX','916':'CA','917':'NY',
    '918':'OK','919':'NC','920':'WI','925':'CA','928':'AZ','929':'NY',
    '931':'TN','936':'TX','937':'OH','940':'TX','941':'FL',
    '947':'MI','949':'CA','951':'CA','952':'MN','954':'FL','956':'TX','959':'CT',
    '970':'CO','971':'OR','972':'TX','973':'NJ','978':'MA','979':'TX','980':'NC',
    '984':'NC','985':'LA','989':'MI'
}

GENERIC_DOMAINS = {
    'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
    'icloud.com','live.com','msn.com','ymail.com','comcast.net',
    'missing.local','invalid.local','example.com',''
}

def run():
    pq = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'
    t0 = time.time()
    print("Loading parquet...")
    df = pd.read_parquet(pq)
    
    us_mask = df['state'] == 'US'
    initial_us = us_mask.sum()
    print(f"Total records: {len(df):,}  |  US placeholders: {initial_us:,}")
    
    # ---- PASS 1: Domain consensus from non-US records ----
    print("\n[PASS 1] Domain consensus matching...")
    def get_domain(email):
        if pd.isna(email) or '@' not in str(email): return None
        d = str(email).split('@')[-1].lower().strip()
        if d in GENERIC_DOMAINS: return None
        return d
    
    df['_domain'] = df['email'].apply(get_domain)
    
    # Build domain->state map from non-US records
    known = df[(df['state'] != 'US') & df['state'].notna() & (df['state'] != '') & df['_domain'].notna()]
    domain_states = known.groupby('_domain')['state'].agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None).dropna().to_dict()
    print(f"  Built domain map: {len(domain_states):,} domains")
    
    p1_mask = us_mask & df['_domain'].notna() & df['_domain'].isin(domain_states)
    df.loc[p1_mask, 'state'] = df.loc[p1_mask, '_domain'].map(domain_states)
    p1_count = p1_mask.sum()
    print(f"  Resolved: {p1_count:,}")
    
    # ---- PASS 2: Company ID consensus ----
    print("\n[PASS 2] Company ID consensus...")
    us_mask = df['state'] == 'US'
    known2 = df[(df['state'] != 'US') & df['state'].notna() & (df['state'] != '') & df['company_id'].notna()]
    company_states = known2.groupby('company_id')['state'].agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None).dropna().to_dict()
    print(f"  Built company map: {len(company_states):,} companies")
    
    p2_mask = us_mask & df['company_id'].notna() & df['company_id'].isin(company_states)
    df.loc[p2_mask, 'state'] = df.loc[p2_mask, 'company_id'].map(company_states)
    p2_count = p2_mask.sum()
    print(f"  Resolved: {p2_count:,}")
    
    # ---- PASS 3: Phone area codes ----
    print("\n[PASS 3] Phone area codes...")
    us_mask = df['state'] == 'US'
    
    def state_from_phone(phone):
        if pd.isna(phone): return None
        digits = re.sub(r'\D', '', str(phone))
        if digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]
        if len(digits) >= 10:
            area = digits[:3]
            return AREA_CODE_TO_STATE.get(area)
        return None
    
    p3_states = df.loc[us_mask, 'phone'].apply(state_from_phone)
    p3_resolved = p3_states.notna()
    df.loc[us_mask & p3_resolved.reindex(df.index, fill_value=False), 'state'] = p3_states[p3_resolved]
    p3_count = p3_resolved.sum()
    print(f"  Resolved: {p3_count:,}")
    
    # ---- PASS 4: Location text (the 199 that had location) ----
    print("\n[PASS 4] Location text extraction...")
    
    STATE_MAP = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
        'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
        'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
        'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
        'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
        'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
        'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
        'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
        'district of columbia': 'DC'
    }
    
    us_mask = df['state'] == 'US'
    has_loc = us_mask & df['location'].notna() & (df['location'] != '')
    
    def extract_state(text):
        if pd.isna(text): return None
        tl = str(text).lower()
        for name, abbr in STATE_MAP.items():
            if name in tl: return abbr
        for name, abbr in STATE_MAP.items():
            if re.search(rf'\b{abbr.lower()}\b', tl): return abbr
        return None
    
    p4_states = df.loc[has_loc, 'location'].apply(extract_state)
    p4_resolved = p4_states.notna()
    df.loc[has_loc & p4_resolved.reindex(df.index, fill_value=False), 'state'] = p4_states[p4_resolved]
    p4_count = p4_resolved.sum()
    print(f"  Resolved: {p4_count:,}")
    
    # ---- Summary ----
    remaining_us = (df['state'] == 'US').sum()
    total_recovered = initial_us - remaining_us
    
    print(f"\n{'='*60}")
    print(f"RECOVERY SUMMARY")
    print(f"{'='*60}")
    print(f"  Pass 1 (Domain consensus):  {p1_count:>10,}")
    print(f"  Pass 2 (Company consensus): {p2_count:>10,}")
    print(f"  Pass 3 (Phone area codes):  {p3_count:>10,}")
    print(f"  Pass 4 (Location text):     {p4_count:>10,}")
    print(f"  ----------------------------------------")
    print(f"  TOTAL RECOVERED:            {total_recovered:>10,}")
    print(f"  REMAINING 'US' placeholder: {remaining_us:>10,}")
    print(f"{'='*60}")
    
    # Drop temp column
    df = df.drop(columns=['_domain'])
    
    # Save
    print("\nSaving parquet...")
    df.to_parquet(pq, index=False, compression='brotli')
    print(f"Done in {time.time() - t0:.1f}s.")

if __name__ == '__main__':
    run()
