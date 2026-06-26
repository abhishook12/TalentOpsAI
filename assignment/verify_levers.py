import pandas as pd
import numpy as np

perf = pd.read_csv('data/campaign_performance.csv').drop_duplicates()
gmv = pd.read_csv('data/seller_category_gmv.csv').drop_duplicates()

total_days = (pd.to_datetime(perf['date']).max() - pd.to_datetime(perf['date']).min()).days + 1

# Active sellers and their categories
perf_agg = perf.groupby(['seller_id', 'category'])['ad_spend'].sum().reset_index()
perf_agg['monthly_ad_spend'] = (perf_agg['ad_spend'] / total_days) * 30
perf_agg['has_ad'] = True

# Merge with GMV
merged = pd.merge(gmv, perf_agg, on=['seller_id', 'category'], how='left')
merged['has_ad'] = merged['has_ad'].fillna(False)

active_sellers = perf['seller_id'].unique()

# Calculate each seller's actual spend-to-GMV ratio where they advertise
active_only = merged[merged['has_ad'] == True]
# Seller level ratio
seller_ratios = active_only.groupby('seller_id').agg({
    'monthly_ad_spend': 'sum',
    'monthly_gmv': 'sum'
}).reset_index()
seller_ratios['seller_ratio'] = seller_ratios['monthly_ad_spend'] / seller_ratios['monthly_gmv']

print("Median seller ratio:", seller_ratios['seller_ratio'].median())

# Lever 2
l2_opps = merged[(merged['seller_id'].isin(active_sellers)) & (~merged['has_ad'])]
l2_with_ratio = pd.merge(l2_opps, seller_ratios[['seller_id', 'seller_ratio']], on='seller_id', how='left')

# Wait, if a seller is active but their GMV is 0 or missing? GMV table has GMV.
l2_with_ratio['incremental_spend'] = l2_with_ratio['monthly_gmv'] * l2_with_ratio['seller_ratio']

print("L2 Untapped GMV:", l2_with_ratio['monthly_gmv'].sum())
print("L2 Incremental Spend:", l2_with_ratio['incremental_spend'].sum())
print("\nL2 Row-level data head:")
print(l2_with_ratio.head())
print("\nL2 Row-level data with largest incremental spend:")
print(l2_with_ratio.sort_values('incremental_spend', ascending=False).head())

# Lever 3
median_ratio = seller_ratios['seller_ratio'].median()
l3_opps = merged[~merged['seller_id'].isin(active_sellers)]
l3_opps['incremental_spend'] = l3_opps['monthly_gmv'] * 0.10 * median_ratio
print("\nL3 Untapped GMV:", l3_opps['monthly_gmv'].sum())
print("L3 Incremental Spend (10% adoption * median ratio):", l3_opps['incremental_spend'].sum())

# Lever 1
perf['utilization'] = perf['ad_spend'] / perf['daily_budget']
constrained = perf[perf['utilization'] >= 0.95]
monthly_constrained = (constrained['ad_spend'].sum() / total_days) * 30
l1_inc = monthly_constrained * 0.30
print(f"\nL1 Monthly Constrained Spend: {monthly_constrained:,.0f}")
print(f"L1 Incremental Spend: {l1_inc:,.0f}")

