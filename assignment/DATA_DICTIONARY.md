# Data Dictionary

Two files, in [`data/`](data/). Currency is **INR (₹)**. This is a raw export from our advertising
platform covering roughly the **last three months** of daily activity (the exact date range is in
the file); seller and campaign IDs are anonymised. **Treat it as you would real production data,
and sanity-check it.**

> New to the terms below (CPC, ROAS, GMV…)? They're all explained in
> [`BACKGROUND.md`](BACKGROUND.md).

---

## `campaign_performance.csv`
**Grain:** one row per **campaign per day**. A campaign belongs to one seller and advertises in
one category.

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | The day (YYYY-MM-DD). |
| `campaign_id` | string | Campaign identifier (e.g. `C1042`). |
| `seller_id` | string | The seller running the campaign (joins to `seller_category_gmv.csv`). |
| `category` | string | The category this campaign advertises in. |
| `daily_budget` | float (₹) | The campaign's daily budget cap. |
| `ad_spend` | float (₹) | Actual spend that day (never exceeds `daily_budget`). This is the marketplace's ad revenue. |
| `impressions` | int | Times the ads were shown. |
| `clicks` | int | Clicks received. |
| `orders` | int | Orders attributed to the ads. |
| `attributed_sales` | float (₹) | Value of sales attributed to the ads (the ad-driven slice of GMV). |

---

## `seller_category_gmv.csv`
**Grain:** one row per **seller per category the seller has sales in** — i.e. the seller's sales
footprint across the marketplace, whether or not they advertise in that category.

| Column | Type | Description |
|--------|------|-------------|
| `seller_id` | string | Seller identifier (e.g. `S2045`). |
| `category` | string | A category this seller has sales in. |
| `monthly_gmv` | float (₹) | The seller's **total** sales in that category in a typical month — ad-driven *and* organic (see GMV vs attributed sales in `BACKGROUND.md`). |

---

## Notes
- **`seller_id` and `category` appear in both files**, so the two can be related.
- **Derived metrics are not stored.** Anything like CPC, CTR, CVR, or ROAS you compute yourself
  from the columns above — nothing is pre-calculated for you.
- Where the data looks off or a definition is ambiguous, note your assumption and proceed.
