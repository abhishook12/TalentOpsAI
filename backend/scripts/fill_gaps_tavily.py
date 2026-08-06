import os
import re
import time
from sqlalchemy import text
from app.database import SessionLocal
from tavily import TavilyClient

from dotenv import load_dotenv
load_dotenv()

# We can rotate keys like in scraper
TAVILY_KEYS = os.getenv("TAVILY_API_KEYS", "").split(",")
current_key_idx = 0

def get_tavily_client():
    global current_key_idx
    if not TAVILY_KEYS or not TAVILY_KEYS[0]:
        return None
    return TavilyClient(TAVILY_KEYS[current_key_idx])

def fill_companies_tavily():
    db = SessionLocal()
    print("Starting Tavily-based Company Enrichment for Top 100 missing...", flush=True)
    
    companies = db.execute(text("""
        SELECT company_id, company_name 
        FROM companies 
        WHERE linkedin_url IS NULL OR TRIM(linkedin_url) = ''
        ORDER BY company_id ASC
        LIMIT 100
    """)).fetchall()
    
    if not companies:
        print("No companies need linkedin enrichment.")
        return
        
    print(f"Found {len(companies)} companies. Enhancing with Tavily...")
    
    client = get_tavily_client()
    if not client:
        print("No Tavily keys found.")
        return
        
    updated = 0
    for cid, name in companies:
        if not name:
            continue
            
        query = f'"{name}" linkedin company profile'
        try:
            response = client.search(query=query, search_depth="basic")
        except Exception as e:
            print(f"Error for {name}: {e}")
            continue
            
        linkedin_url = None
        for result in response.get("results", []):
            url = result.get("url", "")
            if "linkedin.com/company/" in url:
                linkedin_url = url
                break
                
        if linkedin_url:
            db.execute(text("UPDATE companies SET linkedin_url = :url, updated_at = NOW() WHERE company_id = :cid"), {"url": linkedin_url, "cid": cid})
            db.commit()
            updated += 1
            print(f"Enhanced {name} -> {linkedin_url}")
            
    print(f"Finished. Successfully enriched {updated} LinkedIn URLs.")

def fill_industry_from_titles():
    db = SessionLocal()
    print("Inferring Industry from recruiter titles...", flush=True)
    
    # Map common title keywords to industries
    industry_map = {
        'healthcare': 'Healthcare',
        'nurse': 'Healthcare',
        'medical': 'Healthcare',
        'clinical': 'Healthcare',
        'it ': 'Information Technology',
        'tech': 'Information Technology',
        'software': 'Information Technology',
        'engineering': 'Engineering',
        'financial': 'Finance',
        'accounting': 'Finance',
        'legal': 'Legal',
        'retail': 'Retail',
        'manufacturing': 'Manufacturing',
        'executive': 'Executive Search',
        'creative': 'Creative & Marketing'
    }
    
    # Update industry where null based on recruiter title
    for keyword, industry in industry_map.items():
        res = db.execute(text(f"""
            UPDATE companies c
            SET industry = :ind, updated_at = NOW()
            FROM (
                SELECT company_id FROM recruiters 
                WHERE LOWER(title) LIKE :kw 
                GROUP BY company_id
            ) AS sub
            WHERE c.company_id = sub.company_id
              AND (c.industry IS NULL OR TRIM(c.industry) = '')
        """), {"ind": industry, "kw": f"%{keyword}%"})
        db.commit()
        if res.rowcount > 0:
            print(f"Mapped {res.rowcount} companies to {industry} industry.")
            
    print("Industry inference complete.")

if __name__ == "__main__":
    fill_industry_from_titles()
    fill_companies_tavily()
