# TalentOps AI

Recruitment operations intelligence platform — centralize recruiter and company data, ETL import from Excel/CSV, smart ranked search, analytics, and admin tooling.

**Live app**

- Frontend: [talent-ops-ai.vercel.app](https://talent-ops-ai.vercel.app)
- API: [talentopsai-1.onrender.com](https://talentopsai-1.onrender.com)

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Tailwind, Recharts |
| Backend | FastAPI, SQLAlchemy, Pandas |
| Database | PostgreSQL (Neon / local) |
| Deploy | Vercel + Render |

## Local setup

### 1. Database

```powershell
psql -U postgres -c "CREATE DATABASE talentops;"
psql -U postgres -d talentops -f schema.sql
```

### 2. Backend

```powershell
cd backend
copy .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET, ADMIN_PASSWORD
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

App: http://localhost:5173

## Environment variables

### Backend (`backend/.env` or Render)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes for Supabase | Preferred production PostgreSQL connection string |
| `DATABASE_URL` | Fallback | PostgreSQL connection string for local/staging or non-Supabase deployments |
| `JWT_SECRET` | Prod | Strong random string |
| `ADMIN_PASSWORD` | Prod | Platform + admin login password |
| `ENV` | Prod | Set to `production` on Render |
| `CORS_ORIGINS` | Optional | Comma-separated frontend URLs |

### Frontend (Vercel)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL (e.g. `https://talentopsai-1.onrender.com`) |

## Deploy checklist

1. Push to GitHub `main` (Render + Vercel auto-deploy if connected).
2. **Backend host:** set `SUPABASE_DATABASE_URL` or `DATABASE_URL` to the Supabase connection string used by your live database.
3. **Render:** set `ENV=production`, `JWT_SECRET`, `ADMIN_PASSWORD`, `CORS_ORIGINS`.
4. **Vercel:** set `VITE_API_URL` to your backend URL.
5. Change default password — never use `1012` in production.

## Project structure

```
TalentOpsAI/
├── backend/app/     # FastAPI routes, models, ETL
├── frontend/src/    # React pages & components
├── schema.sql       # Initial DB schema + seed
└── README.md
```

## Features (recruiter-focused)

- Smart Search — PostgreSQL `pg_trgm` ranked recruiter search
- Recruiters — CRUD, filters, data quality scores
- State / Company directories
- ETL Upload — column detection + async import jobs
- Analytics — KPIs + visitor tracking
- Admin Terminal — stats, SQL console (SELECT only), visitor logbook

## Author

Abhishek Jadon — portfolio project
