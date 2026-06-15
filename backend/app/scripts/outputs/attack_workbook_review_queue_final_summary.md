# Workbook Review Queue Final Summary

Source workbook: `C:\Users\User\Desktop\final updated sheet.xlsx`

## Applied safe pass
- Known state before: `10,214`
- Known state after: `10,229`
- Unknown state before: `35,191`
- Unknown state after: `35,176`
- Needs review before: `36,271`
- Needs review after: `35,578`
- Safe updates applied: `693`
- Blank-state fills: `15`
- Review-only cleanups: `678`
- Safe-bucket conflicts deferred: `41`

## Bucket breakdown from the full queue
- Auto-fill safe candidates: `734`
- Needs manual review: `32,171`
- Truly unknown: `3,366`

## Top recovery source
- `db_company_majority`: `498` candidates
- `workbook_match`: `32,063`
- `workbook_email`: `174`
- `workbook_name_company`: `150`
- `workbook_phone`: `13`
- `workbook_company_majority`: `7`

## Current live counts
- Total recruiters: `45,405`
- Known state: `10,229`
- Unknown state: `35,176`
- Needs review: `35,578`
- State coverage: `22.5%`

## Key state totals
- IL: `2,234`
- TX: `1,422`
- CA: `1,399`
- PA: `1,256`
- NC: `633`
- NY: `529`
- GA: `386`
- FL: `174`

## Notes
- The second rerun of the recovery script was a no-op for counts and only revalidated the remaining queue.
- No production data was touched, and no push or deploy happened.
