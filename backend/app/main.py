from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import recruiters, candidates, companies, vendors, submissions, analytics, upload

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

@app.on_event("startup")
def auto_import_recruiters():
    import json, os
    from app.database import get_db
    from app.models.models import Recruiter

    json_path = os.path.join(os.path.dirname(__file__), "recruiters.json")
    if not os.path.exists(json_path):
        print("No recruiters.json found, skipping import.")
        return

    db = next(get_db())
    count = db.query(Recruiter).count()
    if count > 0:
        print(f"Recruiters already in DB ({count}), skipping import.")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    added = 0
    for r in data:
        name = r.get("recruiter_name", "").strip()[:150]
        email = r.get("email", "").strip()[:150]
        if not name:
            continue
        db.add(Recruiter(
            recruiter_name=name,
            email=email if email else f"unknown_{added}@noemail.com",
            phone=r.get("phone", "").strip()[:50],
            specialization=r.get("location", "").strip()[:150],
            is_active=True,
        ))
        added += 1
        if added % 500 == 0:
            db.commit()

    db.commit()
    print(f"Auto-imported {added} recruiters.")
