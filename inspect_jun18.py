import pandas as pd
import os

file_path = r"C:\Users\User\Desktop\JUN 18 FOR DATABASW.xlsx"
if os.path.exists(file_path):
    print(f"File found: {file_path}")
    try:
        df = pd.read_excel(file_path, nrows=5)
        print("Columns:", list(df.columns))
        print("First row data:")
        print(df.iloc[0].to_dict())
    except Exception as e:
        print(f"Error reading excel: {e}")
else:
    print(f"File NOT found at {file_path}")
    desktop_files = os.listdir(r"C:\Users\User\Desktop")
    print("Files on desktop:")
    for f in desktop_files:
        if "JUN 18" in f.upper():
            print(" -", f)
