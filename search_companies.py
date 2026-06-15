import os
import pandas as pd

target_companies = [
    'Barrington James', 'Beacon Hill Staffing Group', 'BEACON HILL TECHNOLOGIES', 'BGSF', 'Blackstone Talent Group',
    'BlueWell IT staffing', 'BridgeSource Utilities Solutions', 'Brooksource', 'Byrne Software Technologies', 'C4f',
    'Catasys North America', 'CGITG Company', 'CGSW Information Services, Inc.', 'CMA', 'Concerge Technology Solutions Corp',
    'Corporate Systems Associates, Inc', 'c-resolving partner', 'Curcsurring Services', 'Dandelion Information Technology, Inc.',
    'Data-Hold Inc.', 'Data Base Connection Inc.', 'Design - IT UK', 'Devhill', 'DTE Consulting Solutions', 'dms global',
    'Enterprise Engineering Inc. (EEI)', 'ERP SERVICES', 'Exevo', 'EXCEL CONSULTANTS, INC', 'Exl Service', 'FITRAHS',
    'FastTek Global', 'GASS Staffing, LLC.', 'GDK Inc', 'Global Consulting Services Group LLC', 'Globaltouch Staffing Services',
    'Grand Strategy Group', 'GridGain Systems', 'GSS IT Staffing Inc.', 'Halmosys Consulting', 'Headley Mehta, Inc.',
    'HireGenics', 'Hiresigma Inc.', 'HRLINK Group, Inc.', 'HTC Global Services', 'Huxley', 'IT1 Solutions', 'Hyperams/IT.com',
    'Hyveos, Health', 'I-B-A-M-I Corporation', 'Informatics Consulting Services', 'Innoav Solutions', 'INTEGR IT Solutions',
    'IT Amici, Inc', 'IT Services 2', 'i-t-y-l-a', 'IT Resources', 'KB Staffing', 'Kolo Technologies', 'Konato Software Inc',
    'Kripton Intergalactic Partners (KIP)', 'KRMTech Solutions LLC', 'Kumo Consulting Group', 'LanceTech LLC', 'Linedata',
    'M&S Consulting', 'Makropro LLC', 'Market Maker Inc.', 'MARKEN', 'Medisource', 'Meridian Technologies', 'Mervianna USA LLC',
    'Mastec', 'Navisite', 'Tech Total USA Ltd.', 'TechTech Solutions LLC', 'NTT Data Inc', 'Orange Ecp', 'Paragon IT Professionals',
    'Patidar Recruitment', 'Paypal LLC', 'Peak Consultants', 'Peirce Technical Consulting', 'Penson', 'Penson Systems Incorporated',
    'People Caddie', 'Pipal Tree Services Inc', 'PILLAR IT', 'Pro Staff', 'Project Xtra LLC', 'Prolant Technologies and Consulting',
    'PSI INTERNATIONAL', 'PTYTECH', 'Pyramid Consulting Group, Inc', 'Qanlog Softwa Inc', 'RALPH CLARKE ASSOCIATES',
    'Randstad Technologies', 'Randstad', 'Recruit I.T. Group', 'RedditUSITInc', 'Renesas.IT', 'Roviomat', 'Rizing LLC',
    'RRC Solutions', 'Rughaus Technology Partners, LLC', 'Search Am', 'Search Earth', 'Search Tech', 'Shulman Fleming & Partners',
    'Sigmac & Summerford Associates', 'SiriusComputer Holdings LLC', 'SKRAC', 'Spartan Solutions', 'Stone Oak PR',
    'Strategic Staffing Solutions', 'Strata IQ', 'Summit Tech Partners', 'Syneos', 'Synapting LLC', 'Synectics',
    'Talent Space Inc.', 'Tandym Group', 'Tech One IT', 'The EMMes Group', 'The Hiring Group, LLC', 'The Judge Group Inc.',
    'The Mice Groups, Inc.', 'The Midtown Group', 'The Porter Group', 'The PROS Group', 'The Smith Group',
    'Third Eye Staff and Search, LLC', 'Three Line Solutions', 'TilliBow Enterprises', 'Transmax Solutions', 'Tred Dog Technology',
    'Trillum IT Professional', 'TTC Group', 'U-c-a-r-technology', 'u-e-o-k-a-u-m-a', 'Vaco', 'Valgent', 'Veda Resources',
    'V.R. Repute & Associates, LLC', 'Wood Creek Consulting', 'World View Technology', 'XEN-SOUTH LLC', 'yOh'
]

target_companies_lower = [c.lower() for c in target_companies]

directories = [
    r"c:\TalentOpsAI",
    r"C:\Users\User\Documents",
    r"C:\Users\User\Desktop",
    r"C:\Users\User\Downloads"
]

def search_file(filepath):
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, on_bad_lines='skip', low_memory=False, dtype=str)
        elif filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath, dtype=str)
        else:
            return

        if df.empty:
            return

        df_str = df.fillna('').astype(str).agg(' '.join, axis=1).str.lower()
        
        matches = []
        for company in target_companies_lower:
            mask = df_str.str.contains(company, regex=False)
            if mask.any():
                matched_rows = df[mask]
                for _, row in matched_rows.iterrows():
                    matches.append((company, row.to_dict()))
        
        if matches:
            print(f"\n--- Found matches in {filepath} ---")
            for comp, row in matches:
                print(f"Company Matched: {comp}")
                print(f"Data: {row}")
            print("-" * 40)
    except Exception as e:
        pass

for d in directories:
    if not os.path.exists(d):
        continue
    for root, dirs, files in os.walk(d):
        for file in files:
            if (file.endswith('.csv') or file.endswith('.xlsx')) and not file.startswith('~$'):
                filepath = os.path.join(root, file)
                if 'node_modules' in filepath or '.git' in filepath:
                    continue
                search_file(filepath)

print("\nSearch completed.")
