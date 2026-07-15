import sys
import os
import datetime
from sqlalchemy import text
from app.database import engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path so we can import enrich_recruiter_contacts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

SessionLocal = sessionmaker(bind=engine)

def check_all_companies():
    db = SessionLocal()
    try:
        class FakeDB:
            pass
        args = SimpleNamespace(dry_run=True, apply=False, minimum_confidence=70, batch_size=500, max_updates=500, all_recruiters=True)
        worker = EnrichmentWorker(FakeDB(), args)
        
        print("Fetching unique recruiter names...", flush=True)
        # We also need email to extract new names
        query = """
        SELECT recruiter_name, COUNT(*) as cnt
        FROM recruiters
        GROUP BY recruiter_name
        """
        unique_names = db.execute(text(query)).fetchall()
        print(f"Found {len(unique_names)} unique names.")
        
        non_human_names = set()
        for row in unique_names:
            name, cnt = row
            if name:
                # pass empty company_name to be strict about name being human
                if not worker.is_human_name(name, ""):
                    non_human_names.add(name)
        
        print(f"Found {len(non_human_names)} non-human unique names.")
        
        if non_human_names:
            print("Sample of non-human names found:", list(non_human_names)[:20])
            
            # Now we find all recruiters with these names
            print("Finding affected recruiters to repair...", flush=True)
            # Since there could be thousands of names, we can query in chunks or just fetch email + id + name + company
            names_list = list(non_human_names)
            
            # Write to a file for analysis
            with open("non_human_names_report.txt", "w", encoding="utf-8") as f:
                for n in names_list:
                    f.write(f"{n}\n")
            print("Saved full list of non-human names to non_human_names_report.txt")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_all_companies()
