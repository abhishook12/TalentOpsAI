# TalentOps AI — Project State File
# Drop this file into a new Claude chat to resume instantly

---

## CONTINUATION PROMPT (paste this into new Claude chat)

```
I am building TalentOps AI — a Recruitment Operations Intelligence Platform for my portfolio.
I have attached the project state file which contains everything built so far, the full project
context, and exact instructions on what to build next. Read it fully and continue from where
we left off. Do not ask me to re-explain anything — it is all in the file.
```

---

## 1. WHO IS BUILDING THIS

- Name: Abhishek Jadon
- Role: Data Analyst, 2+ years experience
- Skills: Python (Pandas, NumPy), SQL, Power BI, Looker Studio, ETL, Excel, FastAPI (learning)
- Current companies: Technovion (current), Tek Inspirations, Kochar Tech
- Purpose: Portfolio project to showcase on resume and portfolio website
- Location: Agra/Noida, India

---

## 2. WHAT IS TALENTOPS AI

A Recruitment Operations Intelligence Platform inspired by real staffing workflows.

**The problem it solves:**
American staffing companies (IT consulting) manage recruiters, candidates, vendors, and clients
across Excel sheets and scattered records. This causes duplicate submissions, inconsistent data,
slow reporting, and operational chaos.

**What the platform does:**
- Centralizes recruiter, candidate, vendor, client data
- ETL pipeline for CSV/Excel ingestion with cleaning and deduplication
- Operational analytics dashboards with KPI tracking
- AI-powered natural language search ("Find Java recruiters in Texas on H1B")
- Duplicate detection using fuzzy matching
- Submission pipeline tracking

---

## 3. TECH STACK

| Layer | Technology |
|-------|-----------|
| Frontend | React + Tailwind CSS + Recharts |
| Backend | FastAPI (Python) |
| Database | PostgreSQL 18 |
| Data Processing | Python, Pandas, NumPy |
| AI Layer | Claude API (Anthropic) |
| Deployment | Vercel (frontend) + Render (backend) |
| Dev Tools | VS Code, GitHub, Postman |

---

## 4. USER'S ENVIRONMENT

| Tool | Version | Status |
|------|---------|--------|
| Node.js | v24.15.0 | ✅ Installed |
| Python | 3.14.5 | ✅ Installed |
| PostgreSQL | 18.3 | ✅ Installed + PATH fixed |
| Git | 2.54.0 | ✅ Installed |
| VS Code | Latest | ✅ Installed |
| GitHub account | ✅ Created |
| Vercel account | ✅ Created |
| Render account | ✅ Created |

OS: Windows 10/11
PostgreSQL path: C:\Program Files\PostgreSQL\18\bin

---

## 5. FOLDER STRUCTURE (target)

```
TalentOpsAI/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── recruiter.py
│   │   │   ├── candidate.py
│   │   │   ├── company.py
│   │   │   ├── vendor.py
│   │   │   └── submission.py
│   │   ├── routes/
│   │   │   ├── recruiters.py
│   │   │   ├── candidates.py
│   │   │   ├── companies.py
│   │   │   ├── vendors.py
│   │   │   ├── submissions.py
│   │   │   ├── analytics.py
│   │   │   └── upload.py
│   │   ├── services/
│   │   │   ├── duplicate_detection.py
│   │   │   ├── etl.py
│   │   │   └── ai_search.py
│   │   └── analytics/
│   │       └── kpi_engine.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── charts/
│   │   └── services/
│   ├── package.json
│   └── tailwind.config.js
├── datasets/
│   └── sample_candidates.csv
├── schema.sql          ✅ DONE
└── README.md
```

---

## 6. WHAT HAS BEEN BUILT

### ✅ STEP 1 COMPLETE — PostgreSQL Database Schema (schema.sql)

Full schema includes:

**Tables:**
- `companies` — company_id, company_name, industry, location, website
- `vendors` — vendor_id, vendor_name, contact_name, email, phone, location
- `recruiters` — recruiter_id, name, email, phone, linkedin, specialization, company_id (FK), is_active
- `candidates` — candidate_id, name, email, phone, linkedin, visa_status, skills (TEXT[]), experience_years, location, rate_per_hour, availability, is_duplicate, duplicate_of (self-FK), recruiter_id (FK)
- `submissions` — submission_id, candidate_id (FK), recruiter_id (FK), company_id (FK), vendor_id (FK), job_title, status, submission_date, interview_date, notes
- `users` — user_id, username, email, password_hash, role

**Indexes:** On email, visa_status, skills (GIN), submission status, dates

**Seed data:** 5 companies, 3 vendors, 5 recruiters, 8 candidates, 8 submissions

---

## 7. CURRENT STATUS

- [x] Environment setup complete
- [x] schema.sql written with all tables, indexes, seed data
- [ ] Database created in PostgreSQL (user needs to do this — see Step 8)
- [ ] FastAPI backend
- [ ] Python ETL pipeline
- [ ] React frontend
- [ ] AI layer
- [ ] Deployment

---

## 8. WHAT THE USER NEEDS TO DO NOW (before next Claude builds backend)

Tell the user to run these commands in PowerShell:

```powershell
# Step 1: Open PostgreSQL as superuser
psql -U postgres

# Step 2: Create the database (inside psql prompt)
CREATE DATABASE talentops;

# Step 3: Connect to it
\c talentops

# Step 4: Exit psql
\q

# Step 5: Run the schema file (replace path if different)
psql -U postgres -d talentops -f "C:\TalentOpsAI\schema.sql"
```

They will be asked for a password — this is whatever password they set during PostgreSQL installation.

---

## 9. WHAT TO BUILD NEXT — STEP 2: FastAPI Backend

Build the complete FastAPI backend with:

1. `backend/app/main.py` — FastAPI app entry point with CORS
2. `backend/app/database.py` — SQLAlchemy connection to PostgreSQL
3. `backend/app/models/` — SQLAlchemy ORM models for all 6 tables
4. `backend/app/routes/recruiters.py` — GET, POST, PUT, DELETE /recruiters
5. `backend/app/routes/candidates.py` — GET, POST, PUT, DELETE /candidates with filters (visa, skills)
6. `backend/app/routes/companies.py` — CRUD
7. `backend/app/routes/vendors.py` — CRUD
8. `backend/app/routes/submissions.py` — CRUD + status update
9. `backend/app/routes/analytics.py` — dashboard KPIs endpoint
10. `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy, psycopg2-binary, pandas, python-dotenv
11. `backend/.env.example` — DB connection string template

After backend is done, tell user to:
- `cd backend && pip install -r requirements.txt`
- `uvicorn app.main:app --reload`
- Open http://localhost:8000/docs to verify

---

## 10. FULL BUILD ORDER

| Step | What | Status |
|------|------|--------|
| 1 | PostgreSQL Schema | ✅ DONE |
| 2 | FastAPI Backend | 🔜 NEXT |
| 3 | Python ETL Pipeline | ⏳ Pending |
| 4 | React Frontend | ⏳ Pending |
| 5 | AI Layer (Claude API) | ⏳ Pending |
| 6 | Deploy + README | ⏳ Pending |

---

## 11. RESUME BULLET (for Abhishek's resume when done)

"Designed and developed TalentOps AI, a recruitment operations intelligence platform
centralizing recruiter, candidate, and vendor data with automated ETL pipelines,
duplicate detection, operational analytics dashboards, and AI-powered natural language
search using React, FastAPI, PostgreSQL, and Python."

---

## 12. IMPORTANT NOTES FOR NEXT CLAUDE

- User is non-technical in some areas — always give exact commands to run, never assume
- Always tell user WHEN they need to do something manually
- After each major piece, update this state file and share it as a download
- User's PostgreSQL password was set during installation — prompt them to enter it when needed
- Keep all code production-quality, not tutorial-grade
- The AI layer uses Claude API (Anthropic), not OpenAI
- User has space issues on C: drive — keep dependencies minimal
