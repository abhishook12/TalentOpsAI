# Background — Read This First

> You do **not** need prior advertising experience to do this assignment. This page gives you
> everything you need to understand the business and the problem. Take ~10 minutes with it before
> you open the data — the rest will make much more sense.

---

## 1. What is a marketplace?

A **marketplace** is an online platform (think Amazon, Flipkart, Instacart, Zepto) where many
independent **sellers** list **products** for **shoppers** to buy. The marketplace usually
doesn't own the inventory — it provides the storefront, the traffic, and checkout, and takes a cut.

Three players to keep straight:
- **Shoppers** — people searching and buying.
- **Sellers** (also called **advertisers** when they run ads) — businesses listing products.
- **The marketplace** — the platform itself (this is *us*, the client).

Products are organized into **categories** (Electronics, Beauty, Home, Apparel, …). A single
seller often sells across **several** categories.

---

## 2. What is marketplace advertising?

When a shopper searches "running shoes," the results page shows two kinds of listings:
- **Organic results** — ranked by relevance, free.
- **Sponsored results (ads)** — sellers *pay* to appear in better, more visible spots.

This is called **retail media** or **sponsored product advertising**. It works like an auction:
- A seller creates a **campaign** to promote some products (usually within one category).
- They set a **budget** (e.g. "spend up to ₹3,000/day") and a **bid** (what they'll pay per click).
- When a shopper **clicks** their ad, the seller is charged — this is the **CPC** (cost per click).
- If the shopper then **buys**, that sale is **attributed** to the ad.

**The key money fact:** the seller's ad spend is *paid to the marketplace*. So:

> **The marketplace's ad revenue = the total amount sellers spend on ads.**

To grow ad revenue, the marketplace needs sellers to *spend more* — the same sellers spending
more, sellers advertising in more of their categories, or new sellers starting to advertise.

---

## 3. The metrics you'll see (plain English)

| Metric | What it means | Formula | Good direction |
|--------|---------------|---------|----------------|
| **Impressions** | Times an ad was shown | — | — |
| **Clicks** | Times it was clicked | — | — |
| **CTR** (click-through rate) | % who clicked after seeing it | clicks ÷ impressions | higher = ad is relevant |
| **Ad spend** | What the seller paid (= **our** ad revenue) | clicks × CPC | — |
| **CPC** (cost per click) | Price of one click | ad spend ÷ clicks | lower = cheaper traffic |
| **Orders** | Purchases that came from the ad | — | — |
| **CVR** (conversion rate) | % of clicks that became a purchase | orders ÷ clicks | higher = traffic converts |
| **Attributed sales** | Value of sales the ad drove | — | — |
| **ROAS** ⭐ | **R**eturn **O**n **A**d **S**pend — sales generated per ₹1 of ad spend | attributed sales ÷ ad spend | **higher = ads are more profitable for the seller** |

**ROAS is the metric this whole problem revolves around.** A ROAS of **5** means: for every ₹1 a
seller spent on ads, they got ₹5 of sales back. If ROAS drops to **3**, ads have become less
profitable for that seller.

> **One term to keep straight: GMV vs attributed sales.** **GMV** (gross merchandise value) is a
> seller's **total** sales — ad-driven *and* organic. **Attributed sales** (above) are only the
> slice of GMV that came from ads. The data gives you each seller's total GMV by category, which
> is broader than what ads alone drove.

---

## 4. The core tension (this is the crux — read it twice)

The marketplace wants **more ad revenue** (more seller spend).
Sellers keep spending only if their **ROAS stays healthy** (ads stay profitable for them).

These pull against each other:
- Push *too many* ads or let CPCs run *too high* → sellers' ROAS falls → they cut budgets or stop
  advertising → ad revenue drops in the long run.
- Keep ROAS *very* high but show few ads → leaving revenue on the table.

So the leadership goal — **"grow ad revenue ~20% *without significantly hurting advertiser
profitability (ROAS)*"** — is a balancing act, not a simple "show more ads" lever. A good answer
respects *both* sides.

---

## 5. Three ways to grow ad revenue

Leadership will ask you to size three growth levers. At a high level:
1. **Budget expansion** — getting *existing* campaigns to spend more.
2. **Category expansion** — *existing advertisers* advertising in more of the categories they
   already sell in.
3. **Seller adoption** — bringing sellers who don't advertise yet into advertising.

The brief defines each precisely and tells you what to estimate.

---

## 6. A tiny worked example (illustrative — not the real data)

How the raw numbers turn into the metrics you'll work with. Seller A's campaign, one day: spent
**₹1,000**, got **500 clicks**, and **50** of those clicks bought at **₹100** each.
- CPC = 1,000 ÷ 500 = **₹2.00**
- CVR = 50 ÷ 500 = **10%**
- Attributed sales = 50 × 100 = **₹5,000**
- ROAS = 5,000 ÷ 1,000 = **5.0**

That's it — every metric in Section 3 is built from raw counts like these.

---

## 7. What you'll be asked

The brief lays out the full task. In short: understand **why ROAS is declining**, and **how to
grow ad revenue by ~20% without hurting ROAS** (including sizing the three levers above).

Don't worry about reaching a "textbook" answer — show your reasoning, state your assumptions, and
quantify where you can. That's the job.
