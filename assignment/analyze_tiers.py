import pandas as pd
import numpy as np

perf = pd.read_csv('data/campaign_performance.csv').drop_duplicates()
perf_clean = perf.dropna(subset=['impressions'])

perf_clean['date'] = pd.to_datetime(perf_clean['date'])
perf_clean['week'] = perf_clean['date'].dt.isocalendar().week

# 1. Budget Tier Breakdown
# Let's create budget tiers based on daily_budget distribution
# quartiles:
perf_clean['budget_tier'] = pd.qcut(perf_clean['daily_budget'], q=4, labels=['Low', 'Medium', 'High', 'Very High'])

weekly_tier = perf_clean.groupby(['week', 'budget_tier']).agg({
    'ad_spend': 'sum', 'attributed_sales': 'sum', 'clicks':'sum'
}).reset_index()
weekly_tier['ROAS'] = weekly_tier['attributed_sales'] / weekly_tier['ad_spend']
weekly_tier['CPC'] = weekly_tier['ad_spend'] / weekly_tier['clicks']

pivot_tier = weekly_tier.pivot(index='week', columns='budget_tier', values='ROAS')
print("--- ROAS by Budget Tier ---")
print(pivot_tier)

pivot_cpc_tier = weekly_tier.pivot(index='week', columns='budget_tier', values='CPC')
print("\n--- CPC by Budget Tier ---")
print(pivot_cpc_tier)


# 2. Seller concentration
seller_spend = perf_clean.groupby('seller_id')['ad_spend'].sum().sort_values(ascending=False)
top_20_pct = int(len(seller_spend) * 0.2)
top_sellers = seller_spend.head(top_20_pct).index

perf_clean['seller_tier'] = np.where(perf_clean['seller_id'].isin(top_sellers), 'Top 20% Sellers', 'Bottom 80% Sellers')

weekly_seller = perf_clean.groupby(['week', 'seller_tier']).agg({
    'ad_spend': 'sum', 'attributed_sales': 'sum'
}).reset_index()
weekly_seller['ROAS'] = weekly_seller['attributed_sales'] / weekly_seller['ad_spend']

pivot_seller = weekly_seller.pivot(index='week', columns='seller_tier', values='ROAS')
print("\n--- ROAS by Seller Tier ---")
print(pivot_seller)
