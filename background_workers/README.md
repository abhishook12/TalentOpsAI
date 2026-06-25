# Background Workers

Standalone utilities that do not touch the core FastAPI or React codebase.

## `taxonomy_worker.py`

Normalizes recruiter title signals into one strict category and appends that category into the `tags` field.

### Categories

- `Technology`
- `Healthcare`
- `Executive`
- `Finance`
- `Campus`
- `Legal`
- `General`

### What it does

1. Connects to PostgreSQL with SQLAlchemy.
2. Reads the `recruiters` table in batches.
3. Looks at `title` and `specialization`.
4. Classifies each recruiter into one standard category.
5. Writes a tag like `category: Technology` into `tags`.
6. Replaces older `category:` tags so only one standard category remains.

### How to run

From PowerShell:

```powershell
cd C:\TalentOpsAI\background_workers
$env:DATABASE_URL="your-postgresql-connection-string"
python taxonomy_worker.py
```

Or pass the connection string directly:

```powershell
python taxonomy_worker.py --database-url "your-postgresql-connection-string"
```

### Safe first test

```powershell
python taxonomy_worker.py --dry-run --limit 2000 --batch-size 250
```

### Resume from a point

```powershell
python taxonomy_worker.py --start-id 50000
```

### Useful options

- `--batch-size 1000`
- `--limit 5000`
- `--dry-run`
- `--start-id 25000`
- `--echo-sql`

### Notes

- This worker is isolated from `frontend/` and `backend/`.
- It uses database reflection instead of importing core app models.
- If `tqdm` is installed, you get a progress bar. Otherwise it prints progress updates.

## `bulk_enhancer.py`

Continuously fetches recruiters missing phone numbers from the local API and triggers the backend enhancement endpoint one recruiter at a time with throttling.

### Run

```powershell
cd C:\TalentOpsAI\background_workers
python bulk_enhancer.py
```

### Safe test

```powershell
python bulk_enhancer.py --max-recruiters 10
```

## `discovery_worker.py`

Weekly live-roster discovery scanner for tracked companies.

### What it does

1. Connects directly to PostgreSQL with SQLAlchemy reflection.
2. Loads companies where `is_tracked = True` and `is_active = True`.
3. Searches DuckDuckGo for LinkedIn recruiter profiles related to each company.
4. Checks whether each discovered recruiter already exists.
5. Posts new recruiters to `http://localhost:8000/recruiters/extension`.

### Run one discovery cycle

```powershell
cd C:\TalentOpsAI\background_workers
$env:DATABASE_URL="your-postgresql-connection-string"
python discovery_worker.py --run-once
```

### Dry run

```powershell
python discovery_worker.py --run-once --dry-run --max-companies 5
```

### Continuous weekly mode

```powershell
python discovery_worker.py
```
