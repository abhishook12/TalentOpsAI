import os
import re
import sys
import argparse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Database Setup
def load_database_url() -> str:
    env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("DATABASE_URL")

DB_URL = load_database_url()
if not DB_URL:
    print("Error: DATABASE_URL not found.")
    sys.exit(1)

# Bypass PgBouncer transaction pooler by using Session mode port 5432
DB_URL = DB_URL.replace(":6543", ":5432")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Add dependencies paths
backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.models.models import Company, Recruiter

EMAIL_REGEX = re.compile(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", re.I)

def fetch_portal_emails(url: str) -> list:
    """Visits a company portal and extracts all visible email addresses."""
    if not url or str(url).lower() == 'nan':
        return []
        
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        raw_emails = EMAIL_REGEX.findall(text)
        emails = list(set([e.lower() for e in raw_emails]))
        # Filter out pngs/jpgs that get caught by loose regex
        valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))]
        return valid_emails
    except Exception as e:
        print(f"  [Warn] Failed to scrape {url}: {str(e)}")
        return []

def run_ingestion(filepath: str):
    print(f"Reading file: {filepath}")
    
    # Read without headers to check the first row
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath, header=None)
    elif filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, header=None)
    else:
        print("Unsupported file format. Use .csv or .xlsx")
        return
        
    # Check if first row looks like a header
    first_val = str(df.iloc[0, 0]).lower()
    if "company" in first_val or "name" in first_val:
        # It has headers, re-read with headers
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
            
        col_map = {}
        for c in df.columns:
            clean_c = str(c).lower().strip()
            if "company" in clean_c and "name" in clean_c: col_map[c] = "company_name"
            elif "company" in clean_c and "portal" not in clean_c and "url" not in clean_c: col_map[c] = "company_name"
            elif "portal" in clean_c or "website" in clean_c: col_map[c] = "website"
            elif "linkedin" in clean_c: col_map[c] = "linkedin_url"
            elif "industry" in clean_c: col_map[c] = "industry"
            elif "location" in clean_c: col_map[c] = "location"
            
        df = df.rename(columns=col_map)
    else:
        # No headers, map directly by column index assuming [Company, Website, LinkedIn]
        col_map = {0: "company_name", 1: "website", 2: "linkedin_url"}
        df = df.rename(columns=col_map)

    if "company_name" not in df.columns:
        print("Error: Could not determine 'Company Name' column.")
        print("Available columns:", list(df.columns))
        return

    db = SessionLocal()
    total_processed = 0
    total_emails_found = 0
    
    try:
        for idx, row in df.iterrows():
            c_name = str(row["company_name"]).strip()
            if c_name == 'nan' or not c_name:
                continue
                
            website = str(row.get("website", ""))
            website = website[:255] if website != 'nan' else None
            
            linkedin = str(row.get("linkedin_url", ""))
            linkedin = linkedin[:255] if linkedin != 'nan' else None
            
            industry = str(row.get("industry", ""))
            industry = industry[:100] if industry != 'nan' else None
            
            print(f"Processing: {c_name}")
            
            # 1. Upsert Company
            company = db.query(Company).filter(Company.company_name == c_name).first()
            if not company:
                company = Company(
                    company_name=c_name,
                    is_tracked=True,
                    data_source="file_ingestion"
                )
                db.add(company)
                db.flush() # get ID
            else:
                company.is_tracked = True
                
            if website: company.website = website
            if linkedin: company.linkedin_url = linkedin
            if industry: company.industry = industry
            
            # 2. Scrape Portal for generic recruiters/emails
            if website:
                emails = fetch_portal_emails(website)
                for email in emails:
                    email_lower = email.lower()
                    # Check if email exists
                    existing = db.query(Recruiter).filter(Recruiter.email == email_lower).first()
                    if not existing:
                        r = Recruiter(
                            recruiter_name=email_lower.split("@")[0].replace(".", " ").title(),
                            email=email_lower,
                            company_id=company.company_id,
                            data_source="portal_scrape" # Fixed from source to data_source
                        )
                        db.add(r)
                        total_emails_found += 1
                        print(f"  Found & saved email: {email_lower}")
                        
            db.commit()
            total_processed += 1
            
        print(f"\\n✅ Successfully ingested {total_processed} companies.")
        print(f"✅ Extracted {total_emails_found} direct emails from company portals.")
        print("✅ These companies are now marked as tracked for the DuckDuckGo discovery worker.")
        
    except Exception as e:
        print(f"Fatal error during ingestion: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest targeted companies from CSV/Excel")
    parser.add_argument("--file", type=str, required=True, help="Path to the CSV or Excel file")
    args = parser.parse_args()
    
    run_ingestion(args.file)
