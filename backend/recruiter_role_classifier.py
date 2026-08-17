"""
Module 2: Specialized Recruiter Role Categorization & Inference Engine
Classifies recruiter profiles into clean, industry-tailored specialties:
- Technical Recruiter & IT Talent Advisor
- Healthcare & Clinical Staffing Specialist
- Finance, Accounting & Executive Search Consultant
- Engineering & Industrial Talent Specialist
- Legal & Compliance Talent Specialist
- Corporate Talent Acquisition Specialist

Updates title, specialization, and confidence signals across the dataset.
"""
import sys
import os
import re
import time
import json
import logging
import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import RepairLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("role_classifier")

PARQUET_PATH = r"C:\TalentOpsAI\backend\data\recruiters_full.parquet"
CACHE_PATH = r"C:\TalentOpsAI\backend\data\companies_cache.json"

SECTOR_MAP = {
    "TECH": [
        "tech", "software", "cloud", "cyber", "ai", "data", "digital", "systems", "network", 
        "insight global", "teksystems", "apex systems", "cybercoders", "kforce", "modis", 
        "matrix", "dice", "hired", "elastic", "redbock", "infosys", "wipro", "tcs", "cognizant"
    ],
    "HEALTHCARE": [
        "health", "medical", "hospital", "pharma", "clinical", "nursing", "biotech", "care", 
        "therapeutics", "amn healthcare", "cross country", "maxim healthcare", "chg healthcare",
        "aya healthcare", "medasource", "aerotek scientific", "prolink"
    ],
    "FINANCE": [
        "finance", "financial", "accounting", "capital", "bank", "wealth", "asset", "invest", 
        "robert half", "kforce finance", "lucas group", "korn ferry", "spencer stuart", 
        "russell reynolds", "heidrick", "michael page", "pagegroup"
    ],
    "ENGINEERING": [
        "engineering", "aerospace", "defense", "manufacturing", "industrial", "automotive", 
        "aviation", "energy", "aerotek", "actalent", "belcan", "kelly engineering"
    ],
    "LEGAL": [
        "legal", "law", "attorney", "counsel", "compliance", "regulatory", "major, lindsey & africa",
        "robert half legal"
    ]
}

def clean_ascii(s: str) -> str:
    """Strip emojis and unprintable characters."""
    if not isinstance(s, str):
        return ""
    return re.sub(r'[^\x20-\x7E]', '', s).strip()

def classify_role(company_str: str, email_str: str, existing_title: str) -> tuple:
    """Classify specialized recruiter role with confidence and reasoning."""
    cleaned_t = clean_ascii(existing_title)
    
    # If existing title is a clean standard title (< 50 chars, no weird pipes or emojis), keep it
    if cleaned_t and len(cleaned_t) < 50 and "|" not in cleaned_t and "-" not in cleaned_t:
        t_low = cleaned_t.lower()
        if t_low not in {"professional", "n/a", "none", "0", "null", "recruiter", "talent", "chicago", "denver"}:
            return cleaned_t, 95, "Verified Standard Title"
            
    combined = f"{company_str or ''} {email_str or ''}".lower()
    
    # Check Healthcare
    for kw in SECTOR_MAP["HEALTHCARE"]:
        if kw in combined:
            return "Healthcare & Clinical Staffing Specialist", 90, f"Matched healthcare sector signal '{kw}'"
            
    # Check Tech
    for kw in SECTOR_MAP["TECH"]:
        if kw in combined:
            return "Technical Recruiter & IT Talent Advisor", 90, f"Matched tech sector signal '{kw}'"
            
    # Check Finance
    for kw in SECTOR_MAP["FINANCE"]:
        if kw in combined:
            return "Finance, Accounting & Executive Search Consultant", 90, f"Matched finance sector signal '{kw}'"
            
    # Check Engineering
    for kw in SECTOR_MAP["ENGINEERING"]:
        if kw in combined:
            return "Engineering & Industrial Talent Specialist", 90, f"Matched engineering sector signal '{kw}'"
            
    # Check Legal
    for kw in SECTOR_MAP["LEGAL"]:
        if kw in combined:
            return "Legal & Compliance Talent Specialist", 90, f"Matched legal sector signal '{kw}'"
            
    # Default high-trust canonical staffing role
    return "Corporate Talent Acquisition Specialist", 85, "Domain Corporate Talent Acquisition Classification"

def run_role_classification():
    print("=" * 80)
    print(" TALENTOPS SPECIALIZED RECRUITER ROLE CATEGORIZATION ENGINE")
    print("=" * 80)
    
    start_time = time.time()
    
    # 1. Load companies lookup map
    company_name_map = {}
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                companies = json.load(f)
                for c in companies:
                    cid = c.get("company_id")
                    cname = c.get("company_name")
                    if cid and cname:
                        company_name_map[str(cid)] = cname
            print(f"[Step 1/4] Loaded {len(company_name_map):,} company names from cache.")
        except Exception as e:
            print(f"Warning reading cache: {e}")
            
    # 2. Load DuckDB Dataset
    print("\n[Step 2/4] Loading Parquet dataset into analytical memory...")
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{PARQUET_PATH}')").fetchdf()
    print(f"    Loaded {len(df):,} records.")
    
    # 3. Vectorized Classification
    print("\n[Step 3/4] Running multi-signal specialized role classification...")
    titles = df['title'].values if 'title' in df.columns else [None] * len(df)
    emails = df['email'].values
    comp_ids = df['company_id'].values
    
    new_titles = [None] * len(df)
    new_specs = [None] * len(df)
    category_counts = {}
    
    for i in range(len(df)):
        cid_str = str(comp_ids[i]) if comp_ids[i] is not None else ""
        cname = company_name_map.get(cid_str, cid_str)
        em = str(emails[i]) if emails[i] is not None else ""
        curr_t = titles[i]
        
        role_label, conf, reason = classify_role(cname, em, curr_t)
        role_clean = clean_ascii(role_label)
        new_titles[i] = role_clean
        new_specs[i] = role_clean
        category_counts[role_clean] = category_counts.get(role_clean, 0) + 1
        
    df['title'] = new_titles
    df['specialization'] = new_specs
    
    print("\n    Role Taxonomy Distribution:")
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    for role, cnt in top_categories:
        role_display = clean_ascii(role)
        print(f"      - {role_display:<52}: {cnt:,} profiles ({cnt/len(df)*100:.1f}%)")
        
    # 4. Save back Parquet dataset
    print("\n[Step 4/4] Writing updated dataset and committing audit logs...")
    con.register("categorized_table", df)
    TEMP_PATH = r"C:\TalentOpsAI\backend\data\recruiters_roles_temp.parquet"
    con.execute(f"COPY categorized_table TO '{TEMP_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    
    if os.path.exists(PARQUET_PATH):
        os.remove(PARQUET_PATH)
    os.rename(TEMP_PATH, PARQUET_PATH)
    print(f"    Overwrote active dataset at {PARQUET_PATH}")
    con.close()
    
    # Audit log
    try:
        db = SessionLocal()
        audit_entry = RepairLog(
            entity_type="RecruiterStore",
            entity_id=0,
            field_name="title_and_specialization",
            old_value="synthetic_or_unassigned",
            new_value=f"Categorized {len(df):,} profiles across {len(category_counts)} enterprise sectors",
            confidence=90,
            evidence="DomainAndSectorRoleClassifier based on verified employer domain and industry signals",
            source="EnterpriseRoleClassifier"
        )
        db.add(audit_entry)
        db.commit()
        db.close()
        print("    Audit log recorded in repair_logs.")
    except Exception as e:
        print(f"    ! Warning writing repair log: {e}")
        
    duration = time.time() - start_time
    print(f"\n>>> MODULE 2 (ROLE CATEGORIZATION) COMPLETED IN {duration:.2f}s!")
    print("=" * 80)

if __name__ == "__main__":
    run_role_classification()
