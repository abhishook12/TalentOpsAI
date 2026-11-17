# Database Integrity Audit — 2026-11-16

## Scope

Read-only audit of the configured PostgreSQL database. The review covered entity
volume, person-to-company relationships, source staging, email quality, profile
completeness, location normalization, and canonical-company linkage. No records
were changed.

## Executive result

The database has a solid structural foundation: direct company references are
intact, person names are complete, no prohibited placeholder emails were found,
and populated state values use a standard two-letter format. The main work is
data completion and normalization rather than repair of broken foreign-key links.

| Area | Result | Assessment |
| --- | ---: | --- |
| Recruiter records | 20,075 | Healthy base volume |
| Company records | 39,636 | Large directory; normalization needs work |
| Discovery staging records | 18,435 | Material processing backlog |
| Broken direct recruiter → company links | 0 | Healthy |
| Recruiters without a name | 0 | Healthy |
| Placeholder emails | 0 | Healthy |
| Duplicate populated emails | 0 groups | Healthy |
| Nonstandard populated recruiter states | 0 | Healthy |

## Actionable findings

### High priority

1. **Discovery review backlog — 12,237 records**
   - 66.4% of staging records are awaiting review.
   - This is the largest current bottleneck between discovery and usable catalog data.

2. **Company normalization — 1,974 duplicate normalized-name groups**
   - 3,717 company records share a normalized name but are not linked through a
     canonical or merged relationship.
   - This can split recruiter counts, source history, campaigns, and analytics
     across what is logically the same company.

3. **Email completeness and verification**
   - 814 recruiter profiles have no email.
   - 11 populated emails have an invalid format.
   - 4,477 profiles remain in an unknown email-verification state.

### Medium priority

4. **Profile completeness**
   - 1,002 recruiter profiles have no state.
   - 7,377 recruiter profiles have no LinkedIn URL.
   - 989 profiles are explicitly marked for review.

5. **Company data quality**
   - 25,828 companies have no state.
   - 14,155 companies have low identity confidence.
   - 4 company records have no company name and should be quarantined or repaired.

6. **Duplicate profile signals**
   - 207 duplicate LinkedIn-URL groups need person-resolution review.
   - Do not merge automatically until name, company, and source evidence agree.

### Discovery intake quality

- 11,543 staged discoveries do not yet contain an email.
- 1,913 staged discoveries do not yet contain a company.
- Only 3 staged discoveries do not contain a name.
- Current status distribution: 12,237 review; 2,163 committed; 2,088 promoted;
  1,227 enriched; 467 duplicate-skipped; 252 rejected; 1 held for review.

## Verified strengths

- Direct recruiter-to-company references have no orphaned links.
- Existing company domains are populated.
- No synthetic `@unknown.com` or `@noemail.talentops` addresses were found.
- No duplicate populated recruiter-email groups were found.
- Existing recruiter states are normalized when present.
- 5,705 emails are SMTP-verified, and 3,948 more are pattern-verified.

## Recommended remediation order

1. Process the staging review queue with confidence-based automatic promotion for
   high-evidence records and manual review only for conflicts.
2. Run canonical-company consolidation on the unlinked duplicate name groups,
   preserving provenance and using a reversible merge log.
3. Send missing or unknown-email profiles through the existing deliverability
   gate; retain only verified, pattern-verified, or explicitly reviewable values.
4. Enrich missing state and LinkedIn values from approved source evidence.
5. Resolve duplicate LinkedIn groups using person, company, title, and source
   evidence before merging.
6. Add dashboard KPIs for queue age, unresolved-company duplicates, verified
   email coverage, and profile completeness so quality improvements stay visible.

## Safety note

This audit intentionally made no data changes. Any bulk repair should run in
batches with a dry-run report, provenance retention, and rollback support.
