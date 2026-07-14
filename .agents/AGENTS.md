# Core Operational Rules

1. **Never Remove Data:** Do not delete or remove anyone currently in the database. When adding new people or features, merge them and tag them (e.g., "newly added" or "new feature").
2. **Improve & Align:** Old or existing data/code should only be improved, corrected, fixed, and aligned correctly. 
3. **Local-Only Enforced:** Until explicit permission is given by the user, **everything must be done locally**. Absolutely no code will be pushed to production branches (like `main`) or deployed to live servers (Render/Vercel) without direct authorization.
4. **Maximum Cost/Credit Optimization:** The maximum API credits, bandwidth, and compute resources that can be saved, MUST be saved. Always opt for the most limit-friendly, budget-conscious architecture.
5. **Strict Verification & Push Protocol:** Never push anything to production until the user explicitly says so at least 2 times. Apply the strict implementation and verification protocol to every task: Never mark a task as complete based only on code being added; observe real-world outcomes, cross-check through DB/API/UI, and test edge cases.
6. **Local Verification Loops:** After finishing every task, update, or improvement, verify the change on the local environment at least 4 times with a gap of 1 minute between each check. Provide a screenshot of the local frontend after every check to prove it works. Only after the 4th successful check can you provide the final confirmation to the user.
7. **Strict 450 MB Database Size Limit:** Whatever work or data ingestion is done at any time and to any extent, **the total database size MUST NOT exceed the hard limit of 450 MB**. Always monitor, optimize indexes/types, deduplicate strings, and structure storage strictly to guarantee the database stays below 450 MB.
8. **Platform 70% Limitation Safety Shield & Early Alarm System:** Any platform, hosting provider, or API utilized by this project (e.g., Supabase 5 GB monthly egress/500 MB storage limit, Gemini 15 RPM / 1,000 RPD rate limits, Render 512 MB RAM / 0.1 CPU limit, Vercel 100 GB bandwidth limit) MUST NOT exceed **70% of its maximum platform quota or rate limit** during any operation or task. Whenever any resource consumption hits or crosses the **70% mark** (`3.5 GB` Supabase bandwidth, `315 MB` DB size, `10 RPM` API rate, or `358 MB` server memory), the system MUST immediately halt or throttle non-essential background tasks and trigger an **ALARM** to notify the user instantly so limits are never breached.
9. **Emergency Resource Lockdown & 3-Step Authorization Protocol:** The project includes a full-block **Emergency Resource Shield (`resource_lockdown.py`)** capable of instantly severing all external API calls, background scrapers, and heavy database write operations to protect server resources and budget quotas when critical situations arise or when 70% limits are breached. Whenever the system is placed into Emergency Lockdown (or when starting any high-consumption system/ingestion task after a block), **resuming, restarting, or unblocking the system REQUIRES the user to explicitly say or confirm START/UNBLOCK exactly 3 separate times (3-step verification protocol)**. Never lift a resource lockdown on a single verbal instruction.
10. **Database Search Performance (Ultra-Fast Principle):** Never use regex replacement (`regexp_replace`) or text casts on massive JSON columns (like `metadata_json`, `raw_data`) inside SQL `WHERE` clauses for real-time search endpoints. This triggers full-table sequential scans and destroys performance. Always rely strictly on standard indexed columns (`recruiter_name`, `email`, `phone`, `company_name`, `location`) and `ILIKE`/trigram matches.

# Teams Extractor Architecture & Working Logic

The Teams Extractor is a highly sophisticated, silent background Vision AI bot. Here is exactly how it functions:

1. **True Background Capture (win32gui):** 
   It DOES NOT use standard `pyautogui.screenshot`. It uses Windows deep API (`win32gui.PrintWindow` with `PW_RENDERFULLCONTENT`) to directly extract the graphics buffer of the Microsoft Teams window. This makes it completely immune to Windows notifications, popups, or being hidden behind other windows.

2. **Background Scrolling (WM_MOUSEWHEEL):**
   It DOES NOT hijack the user's mouse. It sends `WM_MOUSEWHEEL` events via `win32gui.PostMessage` directly to the Teams window queue. The user can freely use their mouse on other monitors while the bot works silently.

3. **API Key Round-Robin Rotation:**
   To bypass free-tier rate limits (15 RPM), the bot reads from `api_keys.txt`. If Key A throws a 429 Limit error, the bot instantly catches the exception, updates its internal pointer, and swaps to Key B without skipping a beat.

4. **Stall Detection & Checkpointing:**
   The bot creates perceptual hashes of the screenshots. If 3 consecutive screenshots are identical, it assumes the scroll is finished or stuck, automatically saves the Excel file, and gracefully exits. It also writes a `checkpoint.json` file after every scroll so it can resume exactly where it left off if the program crashes.

5. **JSON Flattening:**
   The Gemini API returns a nested JSON. The Python loop intelligently parses this, flattens the arrays (joining multiple emails with `; `), and dynamically hunts for missing fields like LinkedIn or Location, merging them across screenshot boundaries if a contact is split across two images (`is_continuation_from_above`).
