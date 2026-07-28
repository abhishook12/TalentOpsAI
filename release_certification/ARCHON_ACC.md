# ARCHON Acceptance Criteria Checklist (ACC) for TalentOpsAI Release Certification

## 1. Login Module
- **AC-LOGIN-001**: System must allow Admin to log in using valid email (`admin@talentops.com`) and password.
- **AC-LOGIN-002**: System must allow User to log in using valid email and password.
- **AC-LOGIN-003**: System must reject login attempts with invalid email formats.
- **AC-LOGIN-004**: System must reject login attempts with valid email but incorrect password, displaying a generic error message.
- **AC-LOGIN-005**: System must lock the account after 5 consecutive failed login attempts for 15 minutes.
- **AC-LOGIN-006**: System must redirect Admin to Admin Dashboard upon successful login.
- **AC-LOGIN-007**: System must redirect User to User Dashboard upon successful login.
- **AC-LOGIN-008**: System must terminate session and redirect to login page upon manual logout.

## 2. Google Login Module
- **AC-GLOGIN-001**: System must display a "Login with Google" button on the login screen.
- **AC-GLOGIN-002**: System must successfully authenticate an Admin using a registered Google Workspace account.
- **AC-GLOGIN-003**: System must successfully authenticate a User using a registered Google account.
- **AC-GLOGIN-004**: System must deny access to unauthorized or unregistered Google accounts, displaying an appropriate error message.
- **AC-GLOGIN-005**: System must correctly provision a new User account if Google sign-up is enabled and the domain is whitelisted.

## 3. Dashboard Module
- **AC-DASH-001**: System must display aggregate metrics (Total Recruiters, Active Campaigns, etc.) for Admin role.
- **AC-DASH-002**: System must display user-specific metrics (My Campaigns, Recent Activities) for User role.
- **AC-DASH-003**: System must render real-time charts/graphs properly without console errors.
- **AC-DASH-004**: System must restrict User role from viewing Admin-only metrics (e.g., system-wide revenue, global visitor stats).
- **AC-DASH-005**: System must allow clicking on dashboard widgets to drill down into respective list views.

## 4. Recruiters Module
- **AC-REC-001**: System must display a paginated list of all recruiters to Admin, default 20 per page.
- **AC-REC-002**: System must allow Admin to create a new recruiter with valid data (Name, Email, Company, State).
- **AC-REC-003**: System must prevent Admin from creating a recruiter with a duplicate email address.
- **AC-REC-004**: System must allow Admin to update an existing recruiter's details.
- **AC-REC-005**: System must allow Admin to soft-delete a recruiter.
- **AC-REC-006**: System must allow Admin and User to search recruiters by Name, Email, or Company.
- **AC-REC-007**: System must allow Admin and User to filter recruiters by State and Company.
- **AC-REC-008**: System must restrict User to only view and search recruiters (Read-Only), unless granted specific edit permissions.
- **AC-REC-009**: System must return search results within 2 seconds for a database of 10,000+ recruiters.

## 5. Directory Module
- **AC-DIR-001**: System must display a hierarchical directory starting at the Company level.
- **AC-DIR-002**: System must allow drilling down from Company -> State.
- **AC-DIR-003**: System must allow drilling down from State -> Recruiter list.
- **AC-DIR-004**: System must correctly aggregate counts of recruiters at the Company and State levels.
- **AC-DIR-005**: System must enforce identical view access for both Admin and User roles in the Directory structure.

## 6. Companies Module
- **AC-COMP-001**: System must display a paginated list of companies.
- **AC-COMP-002**: System must allow Admin to perform full CRUD operations on companies.
- **AC-COMP-003**: System must enforce unique company names during creation and update.
- **AC-COMP-004**: System must restrict User role to Read-Only view of companies.
- **AC-COMP-005**: System must allow Admin and User to view detailed company profiles, including associated recruiters.

## 7. Campaigns Module
- **AC-CAMP-001**: System must provide a 4-step workflow for creating a campaign (1: Setup, 2: Audience, 3: Messaging, 4: Review).
- **AC-CAMP-002**: System must allow Admin and User to save a campaign as a draft at any step.
- **AC-CAMP-003**: System must validate all required fields before allowing progression to the next step.
- **AC-CAMP-004**: System must allow Admin to view and manage all campaigns across the system.
- **AC-CAMP-005**: System must restrict User to view and manage only their own created campaigns.
- **AC-CAMP-006**: System must allow Admin and User to pause, resume, or cancel active campaigns.

## 8. AI Search Module
- **AC-AI-001**: System must accept natural language queries in the search bar.
- **AC-AI-002**: System must parse queries and return relevant entities (Recruiters, Companies).
- **AC-AI-003**: System must display AI confidence scores or relevance rankings if applicable.
- **AC-AI-004**: System must handle malformed or nonsensical queries gracefully, returning a "No results found" message.
- **AC-AI-005**: System must ensure User role AI searches do not expose data restricted to Admin role.

## 9. Analytics Module
- **AC-ANAL-001**: System must display comprehensive campaign performance reports (Open rates, Click rates, Replies).
- **AC-ANAL-002**: System must allow date range filtering for all analytics reports.
- **AC-ANAL-003**: System must allow exporting reports to CSV and PDF formats.
- **AC-ANAL-004**: System must provide Admin with cross-user analytics.
- **AC-ANAL-005**: System must restrict User to analytics generated by their own activities.

## 10. Profile Module
- **AC-PROF-001**: System must allow users (Admin and User) to view their own profile details.
- **AC-PROF-002**: System must allow users to update their name, avatar, and contact information.
- **AC-PROF-003**: System must allow users to change their password, requiring the current password for verification.
- **AC-PROF-004**: System must securely hash and store new passwords.

## 11. Settings Module
- **AC-SET-001**: System must allow Admin to configure global application settings (e.g., SMTP, branding, third-party API keys).
- **AC-SET-002**: System must allow User to configure personal notification preferences.
- **AC-SET-003**: System must prevent User from accessing or viewing global application settings.

## 12. Visitor Analytics Module (Admin only)
- **AC-VISIT-001**: System must track and display unique visitor counts, page views, and average session duration.
- **AC-VISIT-002**: System must display geographic location data of visitors.
- **AC-VISIT-003**: System must restrict access to Visitor Analytics strictly to the Admin role.

## 13. Device Approval Module
- **AC-DEV-001**: System must detect login attempts from unrecognized devices.
- **AC-DEV-002**: System must prompt the User to request device approval upon logging in from a new device.
- **AC-DEV-003**: System must send a device approval request to the Admin dashboard.
- **AC-DEV-004**: System must allow Admin to approve or reject device requests.
- **AC-DEV-005**: System must grant the User access immediately upon Admin approval.
- **AC-DEV-006**: System must deny access and notify the User if the device request is rejected.

## 14. Data Quality / SENTINEL (Admin only)
- **AC-SENT-001**: System must periodically scan database records for anomalies (e.g., missing emails, malformed phone numbers).
- **AC-SENT-002**: System must generate a Data Quality report accessible only by Admin.
- **AC-SENT-003**: System must provide Admin with bulk-action tools to merge duplicates or delete invalid records.
- **AC-SENT-004**: System must restrict User role from accessing SENTINEL features.

## 15. Admin Terminal (Admin only)
- **AC-TERM-001**: System must provide a secure, web-based command-line interface for Admin.
- **AC-TERM-002**: System must allow Admin to run predefined maintenance scripts (e.g., cache clear, re-index search).
- **AC-TERM-003**: System must strictly deny access to Admin Terminal for User role.
- **AC-TERM-004**: System must log all commands executed in the Admin Terminal for auditing purposes.

## 16. User Management (Admin only)
- **AC-UM-001**: System must allow Admin to view a paginated list of all system users.
- **AC-UM-002**: System must allow Admin to create, update, and deactivate user accounts.
- **AC-UM-003**: System must allow Admin to assign and modify user roles (Admin vs. User).
- **AC-UM-004**: System must prevent a deactivated user from logging into the system.

## 17. Notifications Module
- **AC-NOTIF-001**: System must display a real-time notification bell with unread count for both Admin and User.
- **AC-NOTIF-002**: System must allow users to mark individual notifications as read.
- **AC-NOTIF-003**: System must allow users to "Mark all as read".
- **AC-NOTIF-004**: System must deliver system-wide broadcasts configured by Admin to all users.
- **AC-NOTIF-005**: System must deliver personal notifications (e.g., campaign completion, device approval status) to specific users.
