import json

with open(r"C:\TalentOpsAI\DATA_QUALITY_BASELINE.json", "r") as f:
    data = json.load(f)

print("================================================================================")
print("CHECK 1: DATASET SIZE, SCHEMA & STORAGE INTEGRITY")
print("================================================================================")
print(f"Total Recruiter Records Analyzed: {data['recruiters']['total']:,}")
print(f"PostgreSQL Companies Registry:    {data['companies_postgres']['total']:,}")
print(f"Distinct Company Keys in Parquet: {data['recruiters']['company_association']['distinct_company_keys']:,}")
print(f"Unique Corporate Domains:         {data['recruiters']['email']['unique_business_domains']:,}")

print("\n================================================================================")
print("CHECK 2: EMAIL, NAME & COMPANY ASSOCIATION QUALITY BREAKDOWN")
print("================================================================================")
em = data['recruiters']['email']
nm = data['recruiters']['names']
co = data['recruiters']['company_association']
print(f"Valid Syntax Emails:       {em['valid_syntax']:,} ({em['valid_syntax_pct']}%)")
print(f"Business Corporate Emails: {em['business_emails']:,} ({em['business_emails_pct']}%)")
print(f"Personal / Free Emails:    {em['personal_or_freemail']:,}")
print(f"Malformed Syntax Emails:   {em['malformed_syntax']:,}")
print(f"Missing / Placeholder:     {em['missing_or_placeholder']:,}")
print(f"Duplicate Email Rows:      {em['total_duplicate_email_rows']:,} ({em['unique_duplicate_emails']} unique pairs)")
print(f"Valid Recruiter Names:     {nm['valid_names']:,} ({nm['valid_names_pct']}%)")
print(f"Malformed Names:           {nm['malformed_names']:,}")
print(f"Mapped Companies:          {co['mapped_company']:,} ({co['mapped_company_pct']}%)")
print(f"Unknown / Placeholder:     {co['unknown_company']:,}")
print(f"Missing Company (NULL):    {co['missing_company']:,}")

print("\n================================================================================")
print("CHECK 3: LOCATION, PROFILES & POSTGRESQL COMPANIES AUDIT")
print("================================================================================")
loc = data['recruiters']['location']
prof = data['recruiters']['profiles']
q = data['recruiters']['quality_tiers']
pg_co = data['companies_postgres']
print(f"Valid US State Codes:      {loc['valid_us_state']:,} ({(loc['valid_us_state']/data['recruiters']['total'])*100:.2f}%)")
print(f"Non-Standard State Codes:  {loc['non_standard_state']:,}")
print(f"Complete City + State:     {loc['complete_city_and_state']:,}")
print(f"Profiles with Phone:       {prof['with_phone']:,}")
print(f"Profiles with Title:       {prof['with_title']:,}")
print(f"Profiles with LinkedIn:    {prof['with_linkedin']:,}")
print(f"PostgreSQL Primary Domains:{pg_co['with_primary_domain']:,} / {pg_co['total']:,}")
print(f"PostgreSQL Verified Logos: {pg_co['with_logo']:,} / {pg_co['total']:,}")
print(f"Current Overall DB Score:  {q['database_avg_score']}% (High Quality: {q['high_quality_pct']}%)")
