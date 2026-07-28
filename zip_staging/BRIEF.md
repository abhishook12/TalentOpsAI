# The Problem — Marketplace Revenue & ROAS Optimization

> New to marketplace advertising? Read **[`BACKGROUND.md`](BACKGROUND.md)** first — it explains
> every term used here in plain language. Then come back to this page.

---

## Business context

You've joined the **ads / monetization** team of an online **marketplace**. Two things have
landed on your desk:

- Over the **last month**, the team has noticed that **overall advertising ROAS is declining** —
  ads are becoming less profitable for our sellers. Left unchecked, that means sellers eventually
  spend less with us.
- At the same time, leadership has set a goal: **grow advertising revenue by ~20% — *without*
  significantly hurting advertiser profitability (ROAS).**

Your analysis will be presented to leadership, **some of whom are not from an advertising
background**, so explain your thinking in business terms, not just metrics.

---

## The data

Two files in [`data/`](data/) — see **[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)** for columns:

- `campaign_performance.csv` — daily performance of advertising campaigns.
- `seller_category_gmv.csv` — every seller's sales by category (whether they advertise or not).

It's a raw export from our ad platform (seller and campaign IDs anonymised), so **sanity-check it
as you would real production data.** Where something is ambiguous, state your assumption and move on.

---

## What we'd like you to deliver

Three objectives. The bullets under each are there to **structure your thinking**, not as a
checklist to mechanically fill — how you investigate is up to you. **State your assumptions, and
put numbers on things wherever you can.**

### Objective 1 — Diagnose the ROAS decline
- Confirm and quantify the decline — how much, and over what period?
- What is actually driving it? Back your explanation with evidence.
- Is this something we should be worried about, and who does it affect?

### Objective 2 — Plan for ~20% ad-revenue growth *while protecting ROAS*
- What does a 20% increase mean in absolute terms (₹), given current ad revenue?
- What concrete actions would get us there **without** materially hurting advertiser ROAS?
  Where is the tension, and how would you manage it?
- How would you measure whether the plan is working — *and* that advertisers aren't being harmed
  in the process?

### Objective 3 — Size the three growth opportunities (in ₹)
Estimate the **incremental monthly ad revenue** available from each lever below, and **state your
assumptions clearly**. Be realistic about *quality of growth*, not just volume.

1. **Budget expansion** — advertisers whose existing campaigns are limited by their daily budgets.
2. **Category expansion** — existing advertisers who sell in categories they **don't yet
   advertise in**.
3. **Seller adoption** — sellers who have real sales but **don't advertise at all**.

Then: **which mix of these would you prioritise to hit the ~20% target, and why?** If the
opportunities overlap, account for it — don't double-count.

---

## What to submit

1. **Your analysis & recommendations** — organised around the three objectives above. Lead with a
   short executive summary a non-technical leader could act on.
2. **Your working** — the queries / notebook / spreadsheet / report / dashboard behind your
   answer, so we can see *how* you got there.
3. **Full AI transcript(s)** — **only if** you used any AI/LLM (see [`README.md`](README.md)).
4. **The tools you used** — a one-line note.

Format is up to you (doc, slides, notebook, sheet — whatever communicates best).

---

## A few notes
- **Time:** aim for a focused day. A few well-defended insights beat a long, shallow report.
- **There's no single right number.** We're reading for your reasoning, your assumptions, and
  whether your recommendations follow from the data.
- **Stuck on a definition?** State a reasonable assumption and proceed.