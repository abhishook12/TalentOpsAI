import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Load and clean data
perf = pd.read_csv('data/campaign_performance.csv')
perf = perf.drop_duplicates()
# Handle null impressions (25 rows) - drop them or just keep them (CTR will ignore nulls)
perf_clean = perf.dropna(subset=['impressions'])

gmv = pd.read_csv('data/seller_category_gmv.csv')
gmv = gmv.drop_duplicates()

# Basic Date Processing
perf_clean['date'] = pd.to_datetime(perf_clean['date'])
perf_clean['week'] = perf_clean['date'].dt.isocalendar().week
perf_clean['month'] = perf_clean['date'].dt.to_period('M')

print("=== Objective 1: ROAS Decline ===")
weekly = perf_clean.groupby('week').agg({
    'ad_spend': 'sum',
    'attributed_sales': 'sum',
    'clicks': 'sum',
    'impressions': 'sum',
    'orders': 'sum'
}).reset_index()

weekly['ROAS'] = weekly['attributed_sales'] / weekly['ad_spend']
weekly['CPC'] = weekly['ad_spend'] / weekly['clicks']
weekly['CVR'] = weekly['orders'] / weekly['clicks']
weekly['CTR'] = weekly['clicks'] / weekly['impressions']
print("Weekly Trends:")
print(weekly[['week', 'ROAS', 'CPC', 'CVR', 'CTR', 'ad_spend', 'attributed_sales']].to_string())

cat_weekly = perf_clean.groupby(['category', 'week']).agg({
    'ad_spend': 'sum',
    'attributed_sales': 'sum'
}).reset_index()
cat_weekly['ROAS'] = cat_weekly['attributed_sales'] / cat_weekly['ad_spend']
cat_pivot = cat_weekly.pivot(index='week', columns='category', values='ROAS')
print("\nCategory Weekly ROAS:")
print(cat_pivot.to_string())

print("\n=== Objective 2: Run Rate ===")
total_days = (perf_clean['date'].max() - perf_clean['date'].min()).days + 1
total_spend = perf_clean['ad_spend'].sum()
monthly_run_rate = (total_spend / total_days) * 30
target_increase = monthly_run_rate * 0.20
print(f"Total Spend (84 days): {total_spend:,.0f}")
print(f"Monthly Run Rate: {monthly_run_rate:,.0f}")
print(f"20% Increase Target: {target_increase:,.0f}")

print("\n=== Objective 3: Levers ===")

# Lever 1: Budget Expansion
perf_clean['utilization'] = perf_clean['ad_spend'] / perf_clean['daily_budget']
constrained_days = perf_clean[perf_clean['utilization'] >= 0.95]
# Let's see how much spend is happening on constrained days
constrained_spend = constrained_days['ad_spend'].sum()
monthly_constrained_spend = (constrained_spend / total_days) * 30
# Assume if we uncap budgets, they spend 30% more on these days
lever1_incremental = monthly_constrained_spend * 0.30
print(f"L1: Monthly constrained spend: {monthly_constrained_spend:,.0f}")
print(f"L1: Incremental spend (assuming 30% lift): {lever1_incremental:,.0f}")

# Lever 2: Category Expansion
# Sellers who advertise in at least one category but not in another where they have GMV
# Get list of (seller, category) with active campaigns
active_seller_cats = perf_clean[['seller_id', 'category']].drop_duplicates()
active_seller_cats['has_ad'] = True

# Get overall ad spend to GMV ratio for active advertisers
# Calculate monthly ad spend per seller per category
seller_cat_spend = perf_clean.groupby(['seller_id', 'category'])['ad_spend'].sum().reset_index()
seller_cat_spend['monthly_ad_spend'] = (seller_cat_spend['ad_spend'] / total_days) * 30

active_perf_gmv = pd.merge(seller_cat_spend, gmv, on=['seller_id', 'category'], how='inner')
overall_spend_gmv_ratio = active_perf_gmv['monthly_ad_spend'].sum() / active_perf_gmv['monthly_gmv'].sum()
print(f"Average Ad Spend / GMV ratio for active pairs: {overall_spend_gmv_ratio:.4f}")

# Find opportunities
gmv_opps = pd.merge(gmv, active_seller_cats, on=['seller_id', 'category'], how='left')
gmv_opps['has_ad'] = gmv_opps['has_ad'].fillna(False)

# Sellers who are active SOMEWHERE
active_sellers = active_seller_cats['seller_id'].unique()
# Untapped categories for active sellers
lever2_opps = gmv_opps[(gmv_opps['seller_id'].isin(active_sellers)) & (~gmv_opps['has_ad'])]
lever2_incremental = lever2_opps['monthly_gmv'].sum() * overall_spend_gmv_ratio
print(f"L2: Untapped GMV for active sellers: {lever2_opps['monthly_gmv'].sum():,.0f}")
print(f"L2: Incremental spend (using avg ratio): {lever2_incremental:,.0f}")

# Lever 3: Seller Adoption
# Sellers who do not advertise AT ALL
inactive_sellers_gmv = gmv_opps[~gmv_opps['seller_id'].isin(active_sellers)]
# Assume 10% adoption rate
lever3_adopted_gmv = inactive_sellers_gmv['monthly_gmv'].sum() * 0.10
lever3_incremental = lever3_adopted_gmv * overall_spend_gmv_ratio
print(f"L3: Total GMV of inactive sellers: {inactive_sellers_gmv['monthly_gmv'].sum():,.0f}")
print(f"L3: Incremental spend (assuming 10% adoption, avg ratio): {lever3_incremental:,.0f}")

