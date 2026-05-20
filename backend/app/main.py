from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.routes import recruiters, candidates, companies, vendors, submissions, analytics, upload, admin
from app.database import get_db, engine
from app.models import models
from app.create_indexes import create_performance_indexes

models.Base.metadata.create_all(bind=engine)
try:
    create_performance_indexes()
except Exception as e:
    print("Error creating indexes at startup:", e)

# Run DB migration for page_visits new columns
try:
    from sqlalchemy.orm import Session
    with Session(engine) as _db:
        admin.migrate_page_visits(_db)
except Exception as e:
    print("Migration warning:", e)

app = FastAPI(
    title="TalentOps AI",
    description="Recruitment Operations Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://talent-ops-ai.vercel.app",
        "http://localhost:5173",
        "*"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(recruiters.router, prefix="/recruiters", tags=["Recruiters"])
app.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(submissions.router, prefix="/submissions", tags=["Submissions"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "TalentOps AI is running", "docs": "/docs"}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

