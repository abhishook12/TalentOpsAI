import os
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google import genai
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.auth_service import get_current_user_from_request
from ..models.auth_models import User

router = APIRouter(prefix="", tags=["AI Integration"], dependencies=[Depends(get_current_user_from_request)])
logger = logging.getLogger(__name__)


# Try to initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Initialization is per-client now

class AISearchQuery(BaseModel):
    query: str

class ResolveDuplicateRequest(BaseModel):
    record_a: Dict[str, Any]
    record_b: Dict[str, Any]

class SmartImportRequest(BaseModel):
    rows: List[Dict[str, Any]]

class BooleanBuilderRequest(BaseModel):
    role: Optional[str] = None
    required_skills: Optional[List[str]] = []
    optional_skills: Optional[List[str]] = []
    excluded_keywords: Optional[List[str]] = []
    location: Optional[str] = None
    job_description: Optional[str] = None

from ..resource_lockdown import track_gemini_call

def get_client():
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set.")
    # Track call to enforce 70% rate limit
    track_gemini_call()
    return genai.Client(api_key=GEMINI_API_KEY)

@router.post("/search-filter")
def ai_search_filter(payload: AISearchQuery):
    """
    Translates a natural language query into JSON filter parameters.
    Prioritizes ultra-fast local keyword/state extraction to save API credits.
    """
    import re
    q_lower = payload.query.lower()
    
    # Ultra-fast local keyword extraction
    state_match = None
    state_map = {
        'texas': 'TX', 'california': 'CA', 'new york': 'NY', 'florida': 'FL', 'illinois': 'IL',
        'georgia': 'GA', 'massachusetts': 'MA', 'washington': 'WA', 'pennsylvania': 'PA',
        'north carolina': 'NC', 'virginia': 'VA', 'ohio': 'OH', 'michigan': 'MI', 'colorado': 'CO'
    }
    for name, code in state_map.items():
        if f"in {name}" in q_lower or f"from {name}" in q_lower or f" {name}" in q_lower:
            state_match = code
            break
    if not state_match:
        m = re.search(r'\b(in|from|at)\s+([a-z]{2})\b', q_lower, re.I)
        if m and m.group(2).upper() in ['TX','CA','NY','FL','IL','GA','MA','WA','PA','NC','VA','OH','MI','CO','NJ','MD','AZ','OR']:
            state_match = m.group(2).upper()

    has_phone = True if ("with phone" in q_lower or "phone number" in q_lower) else None
    missing_email = True if ("missing email" in q_lower or "no email" in q_lower) else None
    
    comp_match = None
    for comp in ['insight global', 'robert half', 'teksystems', 'randstad', 'manpowergroup', 'kforce', 'beacon hill']:
        if comp in q_lower:
            comp_match = comp.title()
            break

    # If local parser found clear filters, return immediately without API call!
    if state_match or comp_match or has_phone is not None or missing_email is not None:
        return {
            "company": comp_match,
            "state": state_match,
            "title": None,
            "has_phone": has_phone,
            "missing_email": missing_email
        }

    # Fallback to Gemini if complex query
    client = get_client()
    prompt = f"""
You are an AI assistant for a recruiter database. Parse the user's natural language search query and return ONLY a valid JSON object. Do NOT use markdown code blocks, return raw JSON string.

Schema to follow:
{{
  "company": "string or null",
  "state": "2-letter abbreviation or null",
  "title": "job title/specialization or null",
  "has_phone": true, false, or null,
  "missing_email": true, false, or null
}}

User Query: "{payload.query}"
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"): text_resp = text_resp[7:]
        if text_resp.endswith("```"): text_resp = text_resp[:-3]
        return json.loads(text_resp.strip())
    except Exception as e:
        logger.error(f"AI Search error: {e}")
        return {"company": None, "state": None, "title": None, "has_phone": None, "missing_email": None}



@router.post("/resolve-duplicate")
def resolve_duplicate(payload: ResolveDuplicateRequest):
    """
    Analyzes two records and returns confidence that they are the same person.
    """
    client = get_client()
    prompt = f"""
You are an expert data analyst. Look at these two recruiter records and determine if they represent the EXACT SAME PERSON.

Record A:
{json.dumps(payload.record_a, indent=2)}

Record B:
{json.dumps(payload.record_b, indent=2)}

Return ONLY a valid JSON object in this format (no markdown code blocks):
{{
  "confidence_score": integer (0 to 100),
  "is_match": boolean (true if > 80),
  "reasoning": "A short 1-2 sentence explanation of your decision."
}}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        return json.loads(text_resp.strip())
    except Exception as e:
        logger.error(f"AI Duplicate Resolver error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-import")
def smart_import(payload: SmartImportRequest):
    """
    Cleans messy CSV rows.
    """
    client = get_client()
    prompt = f"""
You are an expert data cleaner. I am giving you an array of messy CSV rows representing recruiters. 
Clean them up based on these rules:
1. "location": If it contains a city and state, extract the 2-letter state abbreviation into a "state" key, and leave the rest in "location". (e.g. "San Francisco, Calif" -> location: "San Francisco", state: "CA").
2. "recruiter_name": Fix capitalization. If it contains a title like "John Doe - Tech Recruiter", put "John Doe" in "recruiter_name" and "Tech Recruiter" in "title".
3. "email": Ensure it has no spaces.

Messy Rows:
{json.dumps(payload.rows, indent=2)}

Return ONLY a JSON array of the cleaned rows. No markdown code blocks.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        return {"cleaned_rows": json.loads(text_resp.strip())}
    except Exception as e:
        logger.error(f"AI Smart Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/taxonomy-sync")
def ai_taxonomy_sync(db: Session = Depends(get_db)):
    """
    Finds unique un-categorized titles and categorizes them via AI, then bulk updates.
    """
    from sqlalchemy import text
    client = get_client()
    try:
        # 1. Fetch unique uncategorized titles
        rows = db.execute(text("SELECT DISTINCT title FROM recruiters WHERE title IS NOT NULL AND title != '' AND taxonomy_category IS NULL LIMIT 200")).fetchall()
        if not rows:
            return {"message": "All titles are categorized or empty.", "updated_count": 0}
        
        unique_titles = [r[0] for r in rows]
        
        # 2. Ask Gemini to categorize
        prompt = f"""
You are an expert HR data analyst. Group the following recruiter job titles into exactly one of these 8 standard categories:
- Healthcare
- Technology
- Executive
- Finance
- Engineering
- Campus
- Sales
- General/Other

Job Titles to categorize:
{json.dumps(unique_titles)}

Return ONLY a valid JSON dictionary where the keys are the exact job titles provided, and the values are the standard categories. No markdown code blocks.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        
        mapping = json.loads(text_resp.strip())
        
        # 3. Apply the mapping using bulk updates
        updated_count = 0
        for title, category in mapping.items():
            if category not in ["Healthcare", "Technology", "Executive", "Finance", "Engineering", "Campus", "Sales", "General/Other"]:
                category = "General/Other"
            
            res = db.execute(
                text("UPDATE recruiters SET taxonomy_category = :cat WHERE title = :title AND taxonomy_category IS NULL"),
                {"cat": category, "title": title}
            )
            updated_count += res.rowcount
            
        db.commit()
        return {"message": f"Successfully mapped {len(mapping)} unique titles.", "updated_recruiters": updated_count}
    
    except Exception as e:
        db.rollback()
        logger.error(f"AI Taxonomy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/boolean-builder")
def ai_boolean_builder(payload: BooleanBuilderRequest):
    """
    Generates standardized Boolean search queries for LinkedIn Recruiter,
    Google X-Ray searches, and TalentOps platform filters.
    """
    import re
    role = payload.role or ""
    req_skills = payload.required_skills or []
    opt_skills = payload.optional_skills or []
    excluded = payload.excluded_keywords or []
    location = payload.location or ""

    # If raw job description provided, extract key signals
    if payload.job_description and not role:
        lines = [l.strip() for l in payload.job_description.split("\n") if l.strip()]
        if lines:
            role = lines[0][:60]
        # Quick skill extraction from JD
        common_skills = ["React", "Python", "Java", "AWS", "SQL", "Go", "TypeScript", "Node.js", "Kubernetes", "Docker", "DevOps", "Cybersecurity", "Salesforce", "Epic", "C#", ".NET"]
        found = [s for s in common_skills if re.search(r'\b' + re.escape(s) + r'\b', payload.job_description, re.I)]
        if found and not req_skills:
            req_skills = found[:4]

    # Build Title Clause
    title_terms = [t.strip() for t in re.split(r'[,/|]+', role) if t.strip()] if role else ["Recruiter", "Talent Acquisition"]
    title_clause = " OR ".join([f'"{t}"' if " " in t else t for t in title_terms])
    if len(title_terms) > 1:
        title_clause = f"({title_clause})"

    # Build Required Skills Clause
    req_clause = ""
    if req_skills:
        req_parts = [f'"{s}"' if " " in s else s for s in req_skills]
        req_clause = " AND ".join(req_parts)

    # Build Optional Skills Clause
    opt_clause = ""
    if opt_skills:
        opt_parts = [f'"{s}"' if " " in s else s for s in opt_skills]
        opt_clause = f"({' OR '.join(opt_parts)})"

    # Build Excluded Clause
    not_clause = ""
    if excluded:
        not_parts = [f'"{e}"' if " " in e else e for e in excluded]
        not_clause = f"NOT ({' OR '.join(not_parts)})"

    # Assemble LinkedIn String
    linkedin_parts = [f"({title_clause})"]
    if req_clause:
        linkedin_parts.append(req_clause)
    if opt_clause:
        linkedin_parts.append(opt_clause)
    if location:
        linkedin_parts.append(f'"{location}"')
    if not_clause:
        linkedin_parts.append(not_clause)

    linkedin_boolean = " AND ".join([p for p in linkedin_parts if not p.startswith("NOT ")])
    if not_clause:
        linkedin_boolean = f"{linkedin_boolean} {not_clause}"

    # Assemble Google X-Ray
    xray_parts = ["site:linkedin.com/in"]
    if title_clause:
        xray_parts.append(title_clause)
    if req_skills:
        xray_parts.extend([f'"{s}"' if " " in s else s for s in req_skills])
    if location:
        xray_parts.append(f'"{location}"')
    if excluded:
        for e in excluded:
            xray_parts.append(f'-"{e}"')

    google_xray = " ".join(xray_parts)

    # TalentOps internal query
    talentops_keywords = f"{role} {' '.join(req_skills)} {location}".strip()

    return {
        "role": role,
        "extracted_skills": req_skills,
        "talentops_query": talentops_keywords,
        "linkedin_boolean": linkedin_boolean,
        "google_xray_query": google_xray,
        "google_xray_url": f"https://www.google.com/search?q={urllib_quote(google_xray)}"
    }


def urllib_quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)

