from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import recruiters, candidates, companies, vendors, submissions, analytics, upload

app = FastAPI(
    title="TalentOps AI",
    description="Recruitment Operations Intelligence Platform",
    version="1.0.0"
)   

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
)

app.include_router(recruiters.router, prefix="/recruiters", tags=["Recruiters"])
app.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(submissions.router, prefix="/submissions", tags=["Submissions"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

@app.get("/")
def root():
    return {"message": "TalentOps AI is running", "docs": "/docs"}
