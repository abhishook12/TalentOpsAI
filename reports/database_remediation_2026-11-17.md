# Database Integrity Remediation — 2026-11-17

## What was safely repaired

- **36 malformed email values were quarantined.** The original text remains in
  `raw_email_value`; the usable `email` field was cleared, marked `invalid`, and
  set for review. No profile was deleted.
- **2 email values with only a trailing domain dot were normalized.** They were
  kept for review and their original text was retained.
- **1,028 duplicate-LinkedIn candidates are currently marked for review.** None were
  automatically merged because shared LinkedIn URLs need person-and-company
  evidence before consolidation.
- **4 nameless companies were flagged** for repair rather than discarded.
- **3 staging records without a person name were held for review** so they cannot
  enter the catalog as anonymous profiles.

## Safeguards used

- Original malformed email text is retained for recovery and investigation.
- Existing valid email records remain authoritative when a normalization would
  collide with them.
- No recruiter, company, or staging record was deleted.
- No duplicate company or person record was merged automatically.

## Still needs evidence-based resolution

- Duplicate companies need canonical-entity matching before they can be safely
  linked or merged.
- Duplicate LinkedIn candidates need matching names, companies, and source
  history before consolidation.
- Profiles missing company, state, LinkedIn, or deliverable email need enrichment
  rather than guessed data.
- The discovery-review backlog needs an operational review workflow; it is not a
  safe bulk deletion target.

## Verification

Post-repair checks confirmed that no populated recruiter email remains outside
the system's email syntax rule, original values were preserved for quarantined
entries, and the review/hold markers above are present.
