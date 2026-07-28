import pandas as pd
arjun_file = r'C:\Users\User\Downloads\arjun 2nd sheet .xlsx'
print("Reading file...")
df = pd.read_excel(arjun_file, engine='openpyxl')
print("Total rows:", len(df))
if 'EMAIL' in df.columns:
    unique_emails = df['EMAIL'].dropna().astype(str).str.strip().str.lower().nunique()
    print("Unique valid emails:", unique_emails)
else:
    print("No EMAIL column.")
