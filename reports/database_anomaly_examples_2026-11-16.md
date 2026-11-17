# Database Anomaly Examples — Read-only Sample

Personal details are masked. These examples illustrate the largest classes of
issues found in the integrity audit; no records have been changed.

## 1. Unlinked duplicate company groups

| Normalized company key | Records in group | Not linked to a canonical/merged company | Why it matters |
| --- | ---: | ---: | --- |
| `talentgroups` | 205 | 204 | Recruiters, campaigns, and analytics can split across duplicate company entities. |
| `atlanticgrp` | 39 | 39 | Same normalized identity is treated as many separate companies. |
| `revolutiontechnologies` | 41 | 38 | A canonical-company decision is missing for most records. |
| `deltahcp` | 38 | 38 | Duplicate company cluster needs evidence-based consolidation. |
| `corp` | 26 | 26 | This is likely an over-broad normalization key and should be reviewed before any merge. |

**What to fix:** use a dry-run canonical-company resolver. Merge only when domain,
website, location, and source evidence agree. Keep generic keys such as `corp` in
a manual-review queue rather than merging them automatically.

## 2. Invalid email values

| Masked profile | Masked email value | Problem |
| --- | --- | --- |
| A*** | `a***@devtech` | Missing a valid top-level domain. |
| C*** | `c***@.com` | Missing a domain label. |
| D*** | `d***@alpineso` | Missing a valid top-level domain. |
| C*** | `NaN` | Import placeholder stored as an email value. |
| K*** | `@eikon-x.com` | Missing the local-part before `@`. |

**What to fix:** quarantine malformed addresses at import and route them to the
existing email-repair/deliverability pipeline. Do not send outreach to them.

## 3. Duplicate LinkedIn-profile signals

One masked LinkedIn profile identifier is attached to **421 recruiter records**.
The next four duplicate groups contain **19**, **13**, **13**, and **11** records.

**What to fix:** this is too large to auto-merge. First determine whether the
capture process repeatedly saved the same profile, whether agency aliases are
intended, or whether a source parser has a URL-extraction defect. Then merge only
records with matching person and company evidence.

## 4. Discovery staging backlog

| Current state | Records | Without email | Without company |
| --- | ---: | ---: | ---: |
| Review | 12,242 | 9,131 | 1,458 |
| Committed | 2,163 | 1,909 | 360 |
| Promoted | 2,088 | 193 | 31 |
| Enriched | 1,228 | 182 | 10 |
| Rejected | 252 | 131 | 25 |

**What to fix:** prioritize review records that have a reliable name, company,
source URL, and LinkedIn profile. Low-evidence records should remain staged rather
than being promoted into the master catalog.

## Recommended first actions

1. Quarantine the malformed email values above and run a repair dry-run.
2. Investigate the 421-record duplicate LinkedIn cluster before any bulk merge.
3. Canonicalize the high-volume company duplicate groups using domain and website
evidence, beginning with the non-generic keys.
4. Create a review-queue policy that automatically promotes only high-confidence
staged records and surfaces the rest by age and evidence strength.
