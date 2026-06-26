import pandas as pd
import numpy as np

perf_df = pd.read_csv('data/campaign_performance.csv')
gmv_df = pd.read_csv('data/seller_category_gmv.csv')

print("=== Campaign Performance ===")
print(perf_df.info())
print("Duplicates:", perf_df.duplicated().sum())
print("Nulls:\n", perf_df.isnull().sum())
print("Describe:\n", perf_df.describe())

print("\n=== Seller Category GMV ===")
print(gmv_df.info())
print("Duplicates:", gmv_df.duplicated().sum())
print("Nulls:\n", gmv_df.isnull().sum())
print("Describe:\n", gmv_df.describe())

# Check constraints
print("\n=== Constraints ===")
print("Spend > Budget:", (perf_df['ad_spend'] > perf_df['daily_budget']).sum())
print("Date range:", perf_df['date'].min(), "to", perf_df['date'].max())
print("Campaigns:", perf_df['campaign_id'].nunique())
print("Sellers in Perf:", perf_df['seller_id'].nunique())
print("Sellers in GMV:", gmv_df['seller_id'].nunique())
print("Total rows GMV:", len(gmv_df))

# Save the output to a text file to easily read
with open('explore_out.txt', 'w') as f:
    f.write(f"Perf Df Info:\n{perf_df.info()}\n")
