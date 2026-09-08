# TalentOps Scout: The Complete Architectural & Operational Guide

> **Author**: Abhishek Jadon / TalentOps AI Engineering  
> **Target Audience**: Anyone — from non-technical executives and stakeholders to senior software engineers.  
> **Purpose**: A comprehensive, step-by-step explanation of what TalentOps Scout is, how it works, how it captures data, how it validates and cleans information, how it communicates with the cloud, and how it stores intelligence in the master database.

---

## Table of Contents
1. [Executive Summary: What is TalentOps Scout?](#1-executive-summary-what-is-talentops-scout)
2. [The Simple Analogy: How to Explain Scout in 60 Seconds](#2-the-simple-analogy-how-to-explain-scout-in-60-seconds)
3. [The High-Level Architecture](#3-the-high-level-architecture)
4. [The 11-Step Data Journey (From Screen Pixel to Master Database)](#4-the-11-step-data-journey-from-screen-pixel-to-master-database)
   - [Step 1: Win32 Foreground Window Tracking](#step-1-win32-foreground-window-tracking)
   - [Step 2: Strict Target Allowlist & Gatekeeping](#step-2-strict-target-allowlist--gatekeeping)
   - [Step 3: Visual Sampling & 64x64 Regional Diffing](#step-3-visual-sampling--64x64-regional-diffing)
   - [Step 4: Offline Native Windows Media OCR](#step-4-offline-native-windows-media-ocr)
   - [Step 5: ProfileJudge & Structural Signal Inspection](#step-5-profilejudge--structural-signal-inspection)
   - [Step 6: Deep Entity Extraction & Title Intelligence](#step-6-deep-entity-extraction--title-intelligence)
   - [Step 7: Grounding Gate & Anti-Fabrication Guarantee](#step-7-grounding-gate--anti-fabrication-guarantee)
   - [Step 8: Context Memory & Progressive Scroll Assembly](#step-8-context-memory--progressive-scroll-assembly)
   - [Step 9: Local SQLite Buffer & Zero-Loss Sync Queue](#step-9-local-sqlite-buffer--zero-loss-sync-queue)
   - [Step 10: Backend Cloud Ingestion & Batch Intelligence](#step-10-backend-cloud-ingestion--batch-intelligence)
   - [Step 11: Bronze, Silver & Gold Master DB Storage](#step-11-bronze-silver--gold-master-db-storage)
5. [Every Component & File Explained](#5-every-component--file-explained)
   - [Desktop Engine (Client-Side)](#desktop-engine-client-side)
   - [Backend Services (Cloud-Side)](#backend-services-cloud-side)
   - [Web Frontend (Command Center)](#web-frontend-command-center)
6. [Quality Control: How Scout Keeps Garbage Data Out](#6-quality-control-how-scout-keeps-garbage-data-out)
7. [Failure Handling & Resilience: What Happens When Things Go Wrong?](#7-failure-handling--resilience-what-happens-when-things-go-wrong)
8. [Privacy, Security & Resource Efficiency](#8-privacy-security--resource-efficiency)
9. [Summary Cheat-Sheet: Quick Reference Table](#9-summary-cheat-sheet-quick-reference-table)

---

## 1. Executive Summary: What is TalentOps Scout?

**TalentOps Scout** is an autonomous desktop intelligence engine built for talent acquisition teams, recruiters, and sourcers. 

Traditionally, recruiters spend **30% to 50% of their working day manually copying and pasting information**:
- Opening candidate profiles on LinkedIn or messaging threads on MS Teams.
- Copying names, current job titles, company names, work history, education, and contact details.
- Pasting them into spreadsheets or applicant tracking systems (ATS).

**TalentOps Scout completely automates this entire lifecycle.**
It runs silently in the background on the recruiter's computer. As the recruiter browses candidate profiles or chats with talent, Scout **autonomously recognizes relevant candidate information on their screen, reads it using local offline OCR, verifies the data for high quality, and securely syncs it to the centralized TalentOps Master Database** — all with **zero clicks**, zero copying, zero manual data entry, and zero disruption to their regular workflow.

---

## 2. The Simple Analogy: How to Explain Scout in 60 Seconds

If you need to explain Scout to someone who has no technical background, use this analogy of an **Ultra-Smart Executive Assistant sitting beside you**:

1. **The Security Guard at the Door (Window Tracker)**:
   The assistant only looks at your screen when you open a designated work application (like LinkedIn on Google Chrome or a candidate conversation in Microsoft Teams). If you switch to your personal email, YouTube, or banking, the assistant immediately closes their eyes and rests (0% CPU).
2. **The High-Speed Camera with a Motion Sensor (Visual Sampler)**:
   When you look at a candidate profile, the assistant notices that a new profile has appeared or that you just scrolled down to read their work history.
3. **The Instant Reader (Offline OCR)**:
   The assistant reads every line of text visible on that profile in under 100 milliseconds — entirely on your computer, without sending any pictures to the internet.
4. **The Critical Quality Inspector (ProfileJudge & Patterns)**:
   The assistant rejects browser buttons, ads, noise, and navigation menus (like "Ask Gemini", "Bookmarks", or "Search Tabs"). They only accept real human names, real job titles, and real companies.
5. **The Notebook (Local SQLite Queue)**:
   The assistant writes every clean finding into a private local notebook on your machine. Even if your Wi-Fi disconnects, nothing is ever lost.
6. **The Master Filing Clerk (Cloud Batch Intelligence)**:
   Whenever your internet is active, the assistant securely delivers the notebook batches to the TalentOps cloud. The cloud checks if this candidate is brand-new or someone you already have, merges any missing details (phone, email, new promotion), and updates your company's master database.
7. **The Digital Shredder (Evidence Purge)**:
   Once the text is read, any temporary screenshot taken by the assistant is permanently deleted within 15 to 30 seconds. Your hard drive never fills up with pictures.

---

## 3. The High-Level Architecture

```
+-----------------------------------------------------------------------------------+
|                            CLIENT PC (Windows Desktop)                            |
|                                                                                   |
|  [Chrome: LinkedIn] / [MS Teams]                                                  |
|          |                                                                        |
|          v                                                                        |
|  +-----------------------+     +------------------------+                         |
|  | WindowTracker (<1ms)  | --> | VisualSampler (Diffs)  |                         |
|  +-----------------------+     +------------------------+                         |
|                                            |                                      |
|                                            v                                      |
|                                +------------------------+                         |
|                                | Native Windows OCR     | (Offline WinRT)         |
|                                +------------------------+                         |
|                                            |                                      |
|                                            v                                      |
|                                +------------------------+                         |
|                                | ProfileJudge & Noise   |                         |
|                                | Immunity Filters       |                         |
|                                +------------------------+                         |
|                                            |                                      |
|                                            v                                      |
|                                +------------------------+                         |
|                                | EntityExtractor &      |                         |
|                                | TitleNormalizer        |                         |
|                                +------------------------+                         |
|                                            |                                      |
|                                            v                                      |
|                                +------------------------+                         |
|                                | Data Quality Gate      |                         |
|                                +------------------------+                         |
|                                            |                                      |
|                                            v                                      |
|                                +------------------------+                         |
|                                | Local SQLite Queue.db  | (Zero Data Loss Buffer) |
|                                +------------------------+                         |
|                                            |                                      |
+--------------------------------------------|--------------------------------------+
                                             | HTTPS / JWT Encrypted
                                             v
+-----------------------------------------------------------------------------------+
|                             CLOUD BACKEND (FastAPI)                               |
|                                                                                   |
|  POST /recruiters/extension/batch                                                 |
|          |                                                                        |
|          v                                                                        |
|  +-------------------------------------------------------------+                  |
|  | BRONZE LAYER: discovery_staging                             |                  |
|  | (Raw observations, timestamps, device IDs, capture traces)  |                  |
|  +-------------------------------------------------------------+                  |
|          |                                                                        |
|          v                                                                        |
|  +-------------------------------------------------------------+                  |
|  | SILVER LAYER: discovery_processor.py                        |                  |
|  | (Identity resolution, clustering, merge logic, conflict)    |                  |
|  +-------------------------------------------------------------+                  |
|          |                                                                        |
|          v                                                                        |
|  +-------------------------------------------------------------+                  |
|  | GOLD LAYER: recruiters & companies                          |                  |
|  | (Master canonical talent database: 438,800+ profiles)       |                  |
|  +-------------------------------------------------------------+                  |
+-----------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------+
|                        FRONTEND COMMAND CENTER DASHBOARD                          |
|                                                                                   |
|  talent-ops-ai.vercel.app                                                         |
|  - Real-time today's ingestion telemetry (+12 new, +2 enriched, 22 ingested)     |
|  - Geographic choropleth map & state density                                      |
|  - Live staging review queue & manual conflict merge interface                    |
+-----------------------------------------------------------------------------------+
```

---

## 4. The 11-Step Data Journey (From Screen Pixel to Master Database)

### Step 1: Win32 Foreground Window Tracking
Every 600 milliseconds, Scout's `WindowTracker` calls native Windows APIs (`GetForegroundWindow`, `GetWindowTextW`, `GetWindowThreadProcessId`). 
- This check takes less than **1 millisecond** and uses **0% CPU**.
- It asks: *What application is the user looking at right now?*

### Step 2: Strict Target Allowlist & Gatekeeping
Scout enforces a strict security policy:
- **Allowed Targets**:
  1. **Google Chrome** — ONLY when viewing a LinkedIn candidate profile or search results (`linkedin.com/in/*`, `linkedin.com/mynetwork/*`).
  2. **Microsoft Teams** (`ms-teams.exe`) — viewing talent conversations.
- **Strictly Disallowed**:
  - Non-work Chrome tabs: Google Chat (`chat.google.com`), Gmail, YouTube, Google Search, New Tab, Settings.
  - Other apps: Outlook, WhatsApp, Excel, Slack, local folders.
- **Immediate Rest Mode**: If the user switches away to an unsupported tab or app, Scout enters `RESTING_NON_TARGET` mode, stops all screen grabbing, and draws 0% CPU.

### Step 3: Visual Sampling & 64x64 Regional Diffing
When on an allowed window, Scout's `VisualSampler` checks for meaningful visual activity:
- It takes a low-overhead capture of the target window.
- It resizes the capture to a tiny 64x64 grayscale grid and calculates a perceptual pixel difference (`delta`).
- **Scroll & Wakeup Detection**: If the user scrolls down or opens a new candidate, the delta spikes (>3.5%), instantly triggering a high-resolution analysis.
- **Autonomous Periodic Sampling**: Even if the recruiter stops moving their mouse to read a candidate's background, Scout automatically takes an autonomous scan every 3 seconds so no visible data is missed.
- **Duplicate Static Skip**: If the screen hasn't changed at all, Scout computes an MD5 view-hash and skips repeated OCR, saving processing power and battery life.

### Step 4: Offline Native Windows Media OCR
When a meaningful frame is detected:
- Scout feeds the bounding box of the window into the Windows native OCR engine (`Windows.Media.Ocr`).
- **100% Offline & Private**: OCR runs completely locally inside the Windows OS memory. No images or text are sent to third-party vision APIs.
- Speed: Extracts all words and lines with pixel bounding boxes in **under 80 milliseconds**.

### Step 5: ProfileJudge & Structural Signal Inspection
Before parsing names, the `ProfileJudge` evaluates whether the screen actually contains a candidate profile:
- It looks for structural profile anchors: *"Experience"*, *"Education"*, *"About"*, *"Skills"*, connection badges (*"1st"*, *"2nd"*), or headline separators (*"@"*, *"at"*).
- If the recruiter is simply looking at an empty LinkedIn feed, a blank white page, or an ad, ProfileJudge rejects the frame with reason `SYSTEM_NOISE`, and execution stops immediately.

### Step 6: Deep Entity Extraction & Title Intelligence
If the frame passes ProfileJudge, the `EntityExtractor` parses the lines into structured intelligence:
- **Candidate Name**: Isolates the primary human name in the header zone, cleanly stripping degree badges (*"• 2nd"*), pronouns (*"(She/Her)"*), and honorifics (*"Dr."*).
- **Job Title & Company**: Splits complex headlines like *"Senior Talent Partner @ Cyberdyne Systems | AI Engineering"* into:
  - Title: *"Senior Talent Partner"*
  - Company: *"Cyberdyne Systems"*
- **Title Normalizer**: Decomposes the title into:
  - Canonical standardized title (*"Senior Recruiter"*)
  - Seniority level (*"Senior"*, *"VP"*, *"Director"*, *"C-Level"*, *"Lead"*)
  - Domain specialization (*"Talent Acquisition"*, *"Engineering"*, *"Finance"*)
- **Career History**: Multi-line chronological parsing of previous employers, job titles, start/end dates, and tenure months.
- **Education**: Captures universities, degrees (*"BS Computer Science"*), and graduation years.
- **Contact Signals**: Extracts email addresses and phone numbers.
- **Recruiter Signals**: Detects badges like *"Open to Work"* or *"Hiring"*.

### Step 7: Grounding Gate & Anti-Fabrication Guarantee
Scout implements a strict **Zero-Hallucination Grounding Gate**:
- Every extracted observation (e.g. `WORKS_AT: Intelletec`) must be backed by an exact verbatim evidence string found in the OCR lines on the screen.
- If an observation cannot point to physical screen evidence, it is stamped `REJECT_UNGROUNDED` and immediately dropped.

### Step 8: Context Memory & Progressive Scroll Assembly
A single screenshot can rarely show a candidate's entire resume. As the recruiter scrolls down:
- `ContextMemory` tracks the candidate's canonical profile across multiple scroll actions.
- Frame 1 captures Name, Headline, and Location.
- Frame 2 captures Current Role and "About" summary.
- Frame 3 captures Education and Skills.
- ContextMemory seamlessly stitches all 3 frames into a single unified profile cluster without duplicating the candidate.

### Step 9: Local SQLite Buffer & Zero-Loss Sync Queue
Before sending anything over the network, Scout saves the candidate cluster into a local SQLite database on the machine (`local_queue.db`):
- **Idempotency**: Computes a SHA-256 hash of `Name + Company + Source URL`. If the recruiter visits the same profile twice in 24 hours, Scout detects the duplicate and ignores it.
- **Zero Data Loss**: If the recruiter is on an airplane, in a train, or experiencing Wi-Fi drops, observations accumulate safely in the local queue.
- **Exponential Backoff**: If network requests fail, retries back off smoothly (10s, 20s, 40s... up to 300s) to prevent spamming the server.

### Step 10: Backend Cloud Ingestion & Batch Intelligence
The background `BatchProcessor` takes pending items from the local SQLite queue, packages them into a clean JSON payload, and posts them via HTTPS to the TalentOps backend endpoint (`/recruiters/extension/batch`):
- Authenticated with 256-bit scoped JWT tokens.
- Receives the batch, confirms receipt, and marks local queue items as `SYNCED`.

### Step 11: Bronze, Silver & Gold Master DB Storage
In the cloud backend (PostgreSQL on Supabase):
1. **Bronze Layer (`discovery_staging`)**:
   - The raw observation lands in the staging bucket.
   - Preserves raw text, device ID, session ID, capture ID, and forensic timestamps.
2. **Silver Layer (`discovery_processor.py` & `resolved_persons`)**:
   - The Batch Intelligence engine clusters related observations.
   - Calculates weighted identity confidence:
     - LinkedIn URL match: +30%
     - Real email match: +25%
     - Phone match: +15%
     - Company & Name match: +15%
     - Title match: +10%
     - Location match: +5%
   - Matches against existing master database records:
     - If candidate is new with confidence ≥ 70% $\rightarrow$ **Auto-Commit as `NEW_DISCOVERY`**.
     - If candidate exists and has new info $\rightarrow$ **Auto-Update as `ENRICHED`** (records previous company/title).
     - If conflicting data exists (e.g. two conflicting LinkedIn URLs) $\rightarrow$ **Routes to Manual `REVIEW` Queue**.
3. **Gold Layer (`recruiters` & `companies`)**:
   - The verified candidate is written into the central master database (over 438,800 records).
   - Instantly searchable by all recruiters across the company via the Web App and AI Search.

---

## 5. Every Component & File Explained

### Desktop Engine (Client-Side)

| File Path | Component Name | Exact Role & Behavior |
|---|---|---|
| `scout_desktop/app.py` | **Master Application Orchestrator** | Coordinates all desktop modules; manages system tray, polling loop, meaningful frame handler, and Qt event bridge. |
| `scout_desktop/core/window_tracker.py` | **Active Window Tracker** | Calls Win32 APIs every 600ms to detect the foreground application and enforce strict LinkedIn/Teams allowlists. |
| `scout_desktop/core/browser_tracker.py` | **Browser Context Resolver** | Uses Windows UI Automation (COM UIA) to read the active Chrome address bar URL and classify page types (Profile, Search, Feed). |
| `scout_desktop/core/visual_sampler.py` | **Autonomous Visual Sampler** | Runs background screen grabbing, regional grayscale diffing, scroll detection, and 3-second autonomous scanning. |
| `scout_desktop/core/ocr_engine.py` | **Offline Native OCR** | Interfaces with `Windows.Media.Ocr` to perform fast, offline optical character recognition. |
| `scout_desktop/core/evidence_store.py` | **Evidence Lifecycle Manager** | Manages temporary screenshot disk cache with strict 15–30s auto-purge and orphan cleanup. |
| `scout_desktop/core/context_memory.py` | **Continuity Context Memory** | Retains candidate identity across multiple scroll actions, unifying fractured observations. |
| `scout_desktop/extractor/entity_extractor.py` | **Deep Entity Extractor** | Parses raw OCR lines into candidates, companies, education, skills, and employment timelines. |
| `scout_desktop/extractor/semantic_factorizer.py` | **ProfileJudge Noise Filter** | Discriminates real profiles from UI noise, ads, and empty feeds. |
| `scout_desktop/extractor/patterns.py` | **Regex & Pattern Matcher** | Validates names, filters Chrome noise (e.g. *"Ask Gemini"*), validates locations, and extracts connection degrees. |
| `scout_desktop/extractor/title_normalizer.py` | **Title & Seniority Classifier** | Standardizes headlines into canonical job titles, seniority levels, and role families. |
| `scout_desktop/extractor/grounding_gate.py` | **Grounding Gate** | Guarantees that every extracted fact matches visible on-screen evidence. |
| `scout_desktop/extractor/models.py` | **Data Models & Schema** | Defines `Observation`, `EntityCluster`, and `to_staged_contact_dict()` for backend serialization. |
| `scout_desktop/sync/local_queue.py` | **Local SQLite Staging Queue** | Persistent local database (`local_queue.db`) providing offline buffering, idempotency, and backoff. |
| `scout_desktop/sync/backend_client.py` | **Backend REST Client** | Handles device authentication, JWT token caching, heartbeats, and HTTPS payload transmission. |
| `scout_desktop/sync/batch_processor.py` | **Sync Daemon** | Periodically pulls pending records from local queue and synchronizes them to the cloud. |
| `scout_desktop/ui/main_window.py` | **Control Companion UI** | Floating executive widget displaying live discovery counts, recent candidate feed, and telemetry. |
| `scout_desktop/ui/edge_handle.py` | **Edge Dock Handle** | Sleek, collapsible floating pill on screen edge showing live status (Active, Idle, Paused). |
| `scout_desktop/ui/diagnostics_window.py` | **Diagnostics Console** | Deep inspector for system handles, OCR speed, memory consumption, and network logs. |

---

### Backend Services (Cloud-Side)

| File Path | Component Name | Exact Role & Behavior |
|---|---|---|
| `backend/app/routes/extension.py` | **Ingestion API Routes** | Exposes `/recruiters/extension/batch` and `/auto-activate`; ingests raw observation batches into `discovery_staging`. |
| `backend/app/models/staging_models.py` | **Staging Database Models** | Defines the SQLAlchemy schemas for `discovery_staging` (Bronze) and `resolved_persons` (Silver). |
| `backend/app/services/discovery_processor.py` | **Batch Intelligence Engine** | The brain of the staging layer: clusters observations, runs multi-signal identity resolution, checks master database duplicates, and executes auto-merge decisions. |
| `backend/app/routes/staging.py` | **Staging Management API** | Exposes `/staging/summary`, `/staging/records`, and manual review queue merge/approve endpoints. |
| `backend/app/services/ingestion_telemetry.py` | **Telemetry & Audit Service** | Computes real-time today's ingestion metrics, forensic timestamps, and traceable before/after enrichment diffs across the entire system. |
| `backend/app/routes/analytics.py` | **Analytics Endpoints** | Powers the Command Center Dashboard (`/analytics/scraper-ingestion-summary`, `/analytics/visit-stats`). |

---

### Web Frontend (Command Center)

| File Path | Component Name | Exact Role & Behavior |
|---|---|---|
| `frontend/src/pages/Dashboard.jsx` | **Command Center Dashboard** | Main operational overview displaying Master DB count, Enriched Today, Scraper Ingested Today, Queue depth, and Geographic State map. |
| `frontend/src/pages/StagingPipeline.jsx` | **Staging Pipeline Manager** | Dedicated dashboard providing visibility into Bronze/Silver/Gold flow, live clusters, and the conflict review queue. |
| `frontend/src/pages/Recruiters.jsx` | **Master Recruiter Directory** | Searchable table of all 438,800+ canonical candidate records in the master database. |

---

## 6. Quality Control: How Scout Keeps Garbage Data Out

Data quality was Scout's biggest engineering challenge. Below are the **four defensive layers** built into Scout to guarantee only clean, high-grade talent data enters the database:

### Defense 1: Real-Time Tab Switching Protection
*Problem*: If a user switches from LinkedIn to Google Chat, the background scanner might grab a frame while the title still says LinkedIn.  
*Solution*: Scout employs **multi-gate live window re-polling**. Right before OCR starts, Scout queries the operating system directly. If the active window is no longer on LinkedIn, or if the URL reads `chat.google.com`, the frame is dropped instantly.

### Defense 2: The Browser & System Noise Blocklist
*Problem*: OCR reads browser buttons (*"Ask Gemini"*, *"More Tools"*, *"Bookmarks"*), system identifiers (*"DESKTOP-GMM7KIN"*, *"UltraViewer"*), or pagination markers (*"-5"*) as company names or candidate names.  
*Solution*: A dedicated filter blocklist in `patterns.py` automatically eliminates:
- Browser controls: `"ask gemini"`, `"apps"`, `"search"`, `"more tools"`, `"new tab"`, `"bookmarks"`, `"downloads"`.
- Remote desktop tools: `"ultraviewer"`, `"teamviewer"`, `"anydesk"`, `"desktop-"`.
- Bad punctuation: Strings starting or ending with `-%#@;:?!` or strings with >30% non-alphanumeric noise.
- Generic departments: Isolated 2-letter tokens like `IT`, `HR`, `QA`, `UI`, `UX`.

### Defense 3: No Deceptive Title Defaults
*Problem*: Previous scrapers placed the generic word `"Professional"` into any profile without a title.  
*Solution*: Scout never invents titles. If a headline cannot be parsed, the title is stored as an empty string `""`. This allows downstream backend enrichment to populate the actual title later rather than polluting the database with false data.

### Defense 4: Pre-Enqueue Data Quality Gate
Before any candidate record is allowed into the local queue:
- The candidate name must pass human name validation (`is_valid_person_name`).
- If the company name is invalid, it is stripped to `None`.
- If a record has zero professional signals (no title, no company, no email, no phone, no skills), it is rejected as meaningless noise.

---

## 7. Failure Handling & Resilience: What Happens When Things Go Wrong?

| Failure Scenario | What Scout Does | Result |
|---|---|---|
| **Recruiter loses Internet connection** | Continues scanning and storing candidates in `local_queue.db` locally on the hard drive. | Zero data loss. Once Wi-Fi reconnects, all pending items automatically flush to the cloud. |
| **Backend server is down or restarting** | `BatchProcessor` catches the HTTP error, marks retry count, and applies exponential backoff (10s, 20s, 40s... up to 300s). | Prevents server overload; gracefully resumes when backend is healthy. |
| **Recruiter visits the same profile twice** | Computes a SHA-256 hash of `Name + Company + URL`. Detects that this candidate was already synced within the last 24 hours. | Automatically drops the duplicate; saves server bandwidth. |
| **Screen displays sensitive personal content (Banking, Personal Email)** | `WindowTracker` detects non-target window title and process name in <1ms. | Enters `RESTING_NON_TARGET` mode. Grabbing is disabled completely. |
| **Two conflicting profiles share a name** | Silver Layer identity processor detects conflicting LinkedIn URLs or different email domains. | Does not overwrite data; routes candidate to the manual **Review Queue** for recruiter verification. |

---

## 8. Privacy, Security & Resource Efficiency

1. **Zero Cloud Image Storage**:
   Screenshots are only kept in memory or temporary disk cache long enough to perform OCR. Once text is extracted, screenshots are automatically shredded and deleted within **15 to 30 seconds**. No photos are ever uploaded to cloud servers.
2. **0% CPU Idle Consumption**:
   When the recruiter is working in Microsoft Word, reading emails, or typing in Slack, Scout draws **0.0% CPU** by halting image capture loops completely.
3. **End-to-End Encryption**:
   All communication between Scout Desktop and the TalentOps cloud uses TLS 1.3 HTTPS with cryptographically signed JSON Web Tokens (JWT).

---

## 9. Summary Cheat-Sheet: Quick Reference Table

| Question | Answer |
|---|---|
| **What OS does it run on?** | Windows 10 & Windows 11 (64-bit). |
| **What browsers does it monitor?** | Google Chrome (strictly on LinkedIn profiles/search). |
| **What productivity apps are supported?** | Microsoft Teams (candidate chats). |
| **Does it require user interaction?** | No. It is 100% autonomous and zero-click. |
| **Where does OCR happen?** | Offline on the recruiter's computer using Windows native media OCR. |
| **What happens if Wi-Fi disconnects?** | Data accumulates safely in a local SQLite database (`local_queue.db`). |
| **How does it prevent duplicates?** | SHA-256 content hashing on client + multi-signal identity matching on backend. |
| **Where does data finally go?** | TalentOps Master Database (`recruiters` table with 438,800+ profiles). |
| **Where can I monitor it?** | Web Command Center Dashboard (`talent-ops-ai.vercel.app`). |

---
*Document maintained by the TalentOps AI Core Team.*
