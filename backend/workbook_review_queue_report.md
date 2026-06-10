# Workbook Review Queue Report

Source workbook: `C:\Users\User\Desktop\final updated sheet.xlsx`

## What changed
- Safe workbook-backed state recoveries were applied first.
- Remaining blank-state recruiters were then tagged into a review queue.
- No existing good state values were overwritten.

## Final local queue status
- Total recruiters: `45,405`
- Known state: `10,214`
- Unknown state: `35,191`
- Needs review: `36,271`

## Queue breakdown
- Workbook match but no state: `31,411`
- Workbook phone matched but no state: `3,354`
- Workbook email matched but no state: `423`
- Company not strong enough: `2`
- No workbook match: `1`
- Generic unresolved fallback: `4,608`

## Safe workbook recoveries already applied
- Exact email matches: `6`
- Company-majority matches: `211`
- Domain-majority matches: `252`
- Phone exact matches: `19`
- Name + company exact matches: `7`
- Total safe state recoveries: `495`

## State lift from workbook
- CA: `225`
- PA: `102`
- NY: `71`
- IN: `33`
- IL: `18`
- TX: `15`
- AL: `8`
- IA: `6`
- GA: `3`
- FL: `3`

## Deliverables written locally
- `backend/workbook_extraction_report.md`
- `backend/workbook_review_queue_report.md`
- `backend/app/scripts/build_workbook_review_queue.py`

## Notes
- The workbook is a highly merged, noisy source file.
- The review queue now captures the remaining unresolved records instead of leaving them silently blank.
