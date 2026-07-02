#!/usr/bin/env python
"""Inspect Excel Master File - TalentOpsAI"""
import pandas as pd

p = r"C:/Users/User/Downloads/merged_master_final (1).xlsx"
print(f"LOADING {p}...")
xl = pd.ExcelFile(p)
print("Sheet names:", xl.sheet_names)

df = pd.read_excel(p, sheet_name=0, nrows=5)
print("Columns:", df.columns.tolist())
print(df.head(2))
