import openpyxl
FILE = r'C:\Users\User\Desktop\TalentOps_Recruiters_Formatted.xlsx'
wb = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
ws = wb.active
count = 0
for i, row in enumerate(ws.iter_rows(min_row=17, values_only=True)):
    if row[0] and row[1]:
        print(f'Row {i+17}: company_col="{row[0]}", name_col="{row[1]}", email="{row[2]}"')
        count += 1
    if count >= 10: break
