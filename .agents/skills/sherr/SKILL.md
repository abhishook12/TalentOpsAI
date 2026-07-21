---
name: SHERR
description: Activate the SHERR Synchronization, Harmonization & Enterprise Release Review protocol. Triggered by "SHERR", "Run SHERR", "Start SHERR", "SHERR Sync", "SHERR Certification", "SHERR Release Check", "SHERR Cross Verification".
---

# PROJECT SHERR
**Synchronization, Harmonization & Enterprise Release Review**

## Purpose
SHERR is a permanent subsystem of TalentOps AI.

Unlike BARRY, which verifies whether a feature is correct, **SHERR verifies that every approved change has been correctly integrated across the entire application.**

SHERR only starts after:
1. BARRY Pass 1 ✔
2. Engineering Fixes ✔
3. BARRY Pass 2 ✔
4. Engineering Fixes ✔
5. BARRY Pass 3 ✔
6. Final Engineering Review ✔

Only then may SHERR begin.

## Activation
Whenever the user types any of the following commands, SHERR starts automatically:
- `SHERR`
- `Run SHERR`
- `Start SHERR`
- `SHERR Sync`
- `SHERR Certification`
- `SHERR Release Check`
- `SHERR Cross Verification`

## Primary Objective
Whenever any feature is Added, Fixed, Improved, Optimized, Refactored, Redesigned, Removed, or Updated, SHERR must ensure those changes are correctly reflected everywhere they should appear. 
Nothing should exist only on one side of the application unless that behavior is intentional.

## 1. Synchronization Review
For every completed task, SHERR asks: "Where should this change appear?"
Should it affect: Admin, Standard User, Recruiter, Dashboard, Analytics, Campaigns, Profile, Directory, Reports, Notifications, APIs, Database, Logs, Navigation, Permissions.
- If yes... Verify it.
- If no... Verify that it is intentionally hidden.

## 2. Cross-Role Verification
Every completed feature must be tested as:
Administrator -> Standard User -> Recruiter -> Restricted User -> New User -> Existing User -> Expired Session -> Different Browser -> Different Device -> Different Theme.
Every role must receive exactly what it is supposed to receive. No more. No less.

## 3. Reflection Verification
If something changes on one side... SHERR must determine whether it should automatically appear elsewhere.
*Example:* New profile field -> Admin can view -> User can edit -> Database stores it -> API returns it -> Reports include it -> Search indexes it -> Audit log records it -> Analytics updates.
Everything remains synchronized.

## 4. Permission Validation
SHERR must ensure:
- Users cannot access Admin-only functionality.
- Admins can access all administrative functionality.
- Shared functionality behaves identically for all permitted users.
- Role-specific functionality remains isolated.
- No privilege escalation is possible.

## 5. Workflow Validation
For every feature, SHERR verifies the pipeline: Frontend -> Backend -> API -> Database -> Permissions -> Notifications -> Caching -> Analytics -> Logging -> Audit Trail -> Deployment.
Everything must remain consistent.

## 6. Consistency Rules
Every page must follow the project's standards:
- Dark Mode / Light Mode
- Typography, Spacing, Icons, Buttons
- Loading states, Empty states, Animations
- Error handling, Validation, Navigation

## 7. Rule Compliance
SHERR must verify compliance with the project's established engineering rules:
- Architecture rules
- Coding standards
- UI standards
- Performance & Security requirements
- Accessibility
- BARRY requirements
- Project conventions
- State management & Caching rules
- API & Error handling standards
- Logging standards
No new feature may violate existing project rules.

## 8. Regression Synchronization
Whenever something changes... SHERR determines: "What else could this affect?" Then verifies every dependent module.
*Example:* Profile changes -> Campaign Sender -> Authentication -> User Settings -> Admin View -> Audit Logs -> Analytics -> Notifications -> Search.

## 9. Deployment Synchronization
SHERR must compare the local environment with the production environment to verify they are perfectly synced.
It must verify:
- Same feature set.
- Same API behavior.
- Same database schema.
- Same configuration.
- Same permissions.
- Same UI.
- Same workflows.
- Frontend and Backend version hashes match exactly between local and production.
If production does not match local perfectly, SHERR must fail the certification.

## 10. Final Cross Verification
SHERR performs one final complete review to confirm:
- Every approved BARRY fix exists.
- Every improvement is reflected correctly.
- No module was forgotten.
- No synchronization failures exist.
- No permissions were broken.
- No UI inconsistencies exist.
- No regression exists.

## SHERR Report Generation
Generate an artifact (`SHERR_Final_Report.md`) containing:
1. Executive Summary
2. Synchronization Status
3. Cross-role Results
4. Admin Results
5. User Results
6. Permission Results
7. API Results
8. Database Results
9. UI Consistency Results
10. Regression Results
11. Rule Compliance
12. Remaining Issues
13. Final Certification (PASS / FAIL)

## Final Rule
Only after:
✔ BARRY Pass 1 -> Engineering Review
✔ BARRY Pass 2 -> Engineering Review
✔ BARRY Pass 3 -> Engineering Review
✔ SHERR Synchronization
✔ SHERR Cross-Role Verification
✔ SHERR Rule Compliance
✔ SHERR Final Certification

...may a feature be considered production-ready.
If SHERR discovers any issue, the feature returns to development, the necessary fixes are made, and BARRY must be run again before SHERR performs another certification.
