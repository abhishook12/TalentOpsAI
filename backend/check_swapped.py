import openpyxl
import re

FILE = r'C:\Users\User\Desktop\TalentOps_Recruiters_Formatted.xlsx'
wb = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
ws = wb.active

swapped_count = 0
company_keywords = ['llc', 'inc', 'consulting', 'solutions', 'technologies', 'staffing', 'professionals', 'group', 'partners', 'corp', 'tech', 'services', 'systems']

for i, row in enumerate(ws.iter_rows(min_row=17, values_only=True)):
    comp = str(row[0]).strip() if row[0] else ""
    name = str(row[1]).strip() if row[1] else ""
    email = str(row[2]).strip().lower() if row[2] else ""
    
    if not email:
        continue

    # Heuristic: name column contains company keywords
    name_lower = name.lower()
    is_name_company = any(kw in name_lower.split() for kw in company_keywords)
    
    # Heuristic: company column looks like a name (e.g., Steve Vann)
    # and matches the email prefix
    email_prefix = email.split('@')[0]
    comp_letters = re.sub(r'[^a-z]', '', comp.lower())
    prefix_letters = re.sub(r'[^a-z]', '', email_prefix)
    
    comp_matches_email = (len(comp_letters) > 4 and comp_letters in prefix_letters) or (len(prefix_letters) > 4 and prefix_letters in comp_letters)

    if is_name_company or comp_matches_email:
        if swapped_count < 10:
            print(f"Likely swapped - Row {i+17}: company_col='{comp}', name_col='{name}', email='{email}'")
        swapped_count += 1

print(f"\nTotal likely swapped rows found: {swapped_count}")
