# Workbook Extraction Report

Source workbook: `C:\Users\User\Desktop\final updated sheet.xlsx`

## Workbook shape
- Sheets: 1
- Rows: 171,565
- Columns: 198

## Parsed contact set
- Parsed normalized people: 46,967
- Unique workbook emails: 76,474
- DB email overlap: 41,971
- Workbook-only emails: 34,503

## Safe recovery applied locally
- Exact email matches: 6
- Company-majority matches: 211
- Domain-majority matches: 252
- Phone exact matches: 19
- Name+company exact matches: 7
- Total safe local recoveries: 495

## Local DB impact
- Known state before workbook pass: 9,719
- Unknown state before workbook pass: 35,686
- Known state after workbook pass: 10,214
- Unknown state after workbook pass: 35,191

## State lift from workbook recovery
- CA: 225 recovered
- PA: 102 recovered
- NY: 71 recovered
- IN: 33 recovered
- IL: 18 recovered
- TX: 15 recovered
- AL: 8 recovered
- IA: 6 recovered
- GA: 3 recovered
- FL: 3 recovered

## Remaining unknowns by reason
- Workbook match but no state: 31,411
- Workbook phone matched but no state: 3,354
- Workbook email matched but no state: 423
- Company not strong enough: 2
- No workbook match: 1

## Notes
- Recovery was applied only to blank-state records.
- Evidence was stored in `metadata_json` under `workbook_recovery`.
- The workbook is still very noisy and merged, so the remaining unknowns should be treated as genuinely unresolved unless more source context becomes available.
