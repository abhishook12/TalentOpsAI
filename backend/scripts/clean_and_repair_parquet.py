import os
import re
import shutil
import time
import duckdb

PARQUET_PATH = os.path.abspath(r"c:\TalentOpsAI\backend\data\recruiters_full.parquet")
BACKUP_PATH = os.path.abspath(r"c:\TalentOpsAI\backend\data\recruiters_full.parquet.bak")
TEMP_PATH = os.path.abspath(r"c:\TalentOpsAI\backend\data\recruiters_full_repaired.parquet")

def clean_name_udf(name):
    if not name or not isinstance(name, str):
        return name
    
    s = name.strip()
    s_lower = s.lower()
    
    # 1. System / DocuSign / Event / LinkedIn UI noise
    if "docusign" in s_lower or ("america" in s_lower and "cup" in s_lower) or "degree connection" in s_lower or "has a premium" in s_lower:
        return ""
        
    # 2. "Name" Via Mailing List
    if " via " in s_lower:
        via_match = re.match(r'^[\'"]?([^\'"]+?)[\'"]?\s+via\s+', s, flags=re.IGNORECASE)
        if via_match:
            clean = via_match.group(1).strip().strip('"\'')
            return clean.title()
        else:
            clean = s.split(" via ")[0].strip().strip('"\'')
            return clean.title()
            
    # 3. DBA (Doing Business As) & Professional Credentials
    if " dba " in s_lower or " d/b/a " in s_lower:
        parts = re.split(r'\s+d/?b/?a\s+', s, flags=re.IGNORECASE)
        clean = parts[0].strip().strip('"\'')
        return clean.title()

    # 4. Pure Job Titles Saved as Name
    title_start = {"vice president", "vp", "director", "manager", "recruiter", "recruiting", "sourcer", "consultant", "specialist", "principal", "chief", "lead", "head"}
    if any(s_lower.startswith(ts) for ts in title_start) and any(kw in s_lower for kw in ["specialist", "recruiting", "management", "consultant", "talent", "staffing", "services"]):
        return ""
        
    # 5. Stray Quotes
    if s.startswith(('"', "'")) or s.endswith(('"', "'")):
        clean = s.strip('"\' ')
        return clean.title()
        
    return s

def run_cleaning_pipeline():
    start_time = time.time()
    print("=" * 80)
    print("STARTING DUCKDB PARQUET SANITIZATION & REPAIR PIPELINE")
    print("=" * 80)
    
    # 1. Backup original parquet file
    if not os.path.exists(BACKUP_PATH):
        print(f"Creating backup: {BACKUP_PATH}...")
        shutil.copy2(PARQUET_PATH, BACKUP_PATH)
        print("Backup created successfully.")
    else:
        print(f"Backup already exists at: {BACKUP_PATH}")
        
    con = duckdb.connect()
    
    # Register UDF
    con.create_function("clean_name_udf", clean_name_udf, ["VARCHAR"], "VARCHAR")
    
    print("Loading parquet data into DuckDB table...")
    con.execute(f"CREATE TABLE recruiters_clean AS SELECT * FROM read_parquet('{PARQUET_PATH}')")
    
    initial_count = con.execute("SELECT COUNT(*) FROM recruiters_clean").fetchone()[0]
    print(f"Total Initial Rows: {initial_count:,}")
    
    # Update names with UDF
    print("Applying clean_name_udf across all 437,933 records...")
    con.execute("""
        UPDATE recruiters_clean 
        SET recruiter_name = clean_name_udf(recruiter_name)
    """)
    
    # Deactivate / Purge rows where name became empty or NULL (DocuSign, sports events, pure job titles)
    print("Updating active status and review flags for purged noise...")
    con.execute("""
        UPDATE recruiters_clean 
        SET is_active = FALSE,
            needs_review = TRUE,
            review_reason = 'PURGED_NON_PERSON_METADATA'
        WHERE recruiter_name = '' OR recruiter_name IS NULL
    """)
    con.execute("UPDATE recruiters_clean SET recruiter_name = NULL WHERE recruiter_name = ''")
    
    # Invalidate Google Groups distribution list emails
    print("Marking @googlegroups.com emails as non-deliverable mailing lists...")
    con.execute("""
        UPDATE recruiters_clean 
        SET is_deliverable = FALSE,
            email_status = 'mailing_list_group'
        WHERE email ILIKE '%@googlegroups.com%'
    """)
    
    # Sync normalized_recruiter_name
    print("Updating normalized_recruiter_name...")
    con.execute("""
        UPDATE recruiters_clean 
        SET normalized_recruiter_name = LOWER(recruiter_name)
        WHERE recruiter_name IS NOT NULL
    """)
    
    # Export to temp parquet file
    print(f"Writing repaired dataset to temporary parquet file: {TEMP_PATH}...")
    con.execute(f"COPY recruiters_clean TO '{TEMP_PATH}' (FORMAT PARQUET)")
    
    con.close()
    
    # Replace original file atomically
    print("Atomically replacing original parquet file...")
    os.replace(TEMP_PATH, PARQUET_PATH)
    
    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"PARQUET SANITIZATION COMPLETED IN {elapsed:.2f} SECONDS!")
    print("=" * 80)

if __name__ == "__main__":
    run_cleaning_pipeline()
