import os
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import google.generativeai as genai
from sqlalchemy.orm import Session
from ..database import get_db

router = APIRouter(prefix="/ai", tags=["AI Integration"])
logger = logging.getLogger(__name__)

# Try to initialize Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AISearchQuery(BaseModel):
    query: str

class ResolveDuplicateRequest(BaseModel):
    record_a: Dict[str, Any]
    record_b: Dict[str, Any]

class SmartImportRequest(BaseModel):
    rows: List[Dict[str, Any]]

def get_model():
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set.")
    # Use flash for speed
    return genai.GenerativeModel('gemini-2.5-flash')

@router.post("/search-filter")
def ai_search_filter(payload: AISearchQuery):
    """
    Translates a natural language query into JSON filter parameters.
    Returns: {"company": "", "state": "", "title": "", "has_phone": null, "missing_email": null}
    """
    model = get_model()
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

Examples:
Query: "show me healthcare recruiters in texas with a phone number"
Response: {{"company": null, "state": "TX", "title": "healthcare", "has_phone": true, "missing_email": null}}

Query: "recruiters at microsoft missing an email"
Response: {{"company": "microsoft", "state": null, "title": null, "has_phone": null, "missing_email": true}}

User Query: "{payload.query}"
"""
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        # Clean up possible markdown code blocks
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        return json.loads(text_resp.strip())
    except Exception as e:
        logger.error(f"AI Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-duplicate")
def resolve_duplicate(payload: ResolveDuplicateRequest):
    """
    Analyzes two records and returns confidence that they are the same person.
    """
    model = get_model()
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
        response = model.generate_content(prompt)
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
    model = get_model()
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
        response = model.generate_content(prompt)
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
def ai_taxonomy_sync():
    """
    Finds unique un-categorized titles and categorizes them via AI, then bulk updates.
    """
    from sqlalchemy import text
    model = get_model()
    db: Session = next(get_db())
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
        response = model.generate_content(prompt)
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
