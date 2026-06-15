import pandas as pd
from sqlalchemy import text
from app.database import SessionLocal
from app.utils.state_mapper import extract_state_detailed

def run_recovery():
    print("Loading source files...", flush=True)
    
    # 1. Load Master Sheet
    master_path = "C:/Users/User/Desktop/for location by claude/1 the below all compny but location wise/Recruiter_Contacts_Master.xlsx"
    df_master = pd.read_excel(master_path, dtype=str)
    
    # 2. Load State Wise Sheet
    state_path = "C:/Users/User/Downloads/Companies_data_state_wise.xlsx"
    df_state = pd.read_excel(state_path, dtype=str)
    
    # Build maps mapping email -> (location, state, company)
    email_map = {}
    
    print("Parsing Master sheet...", flush=True)
    for _, row in df_master.iterrows():
        email = str(row.get('Email', '')).strip().lower()
        if not email or email == 'nan':
            continue
            
        loc = str(row.get('Location', '')).strip()
        comp = str(row.get('Company', '')).strip()
        
        loc = None if loc == 'nan' else loc
        comp = None if comp == 'nan' else comp
        
        email_map[email] = {
            'location': loc,
            'state': None,
            'company': comp
        }
        
    print("Parsing State sheet...", flush=True)
    for _, row in df_state.iterrows():
        email = str(row.get('Email', '')).strip().lower()
        if not email or email == 'nan':
            continue
            
        state_str = str(row.get('State', '')).strip()
        comp = str(row.get('Company', '')).strip()
        
        state_str = None if state_str == 'nan' else state_str
        comp = None if comp == 'nan' else comp
        
        # State sheet has explicit states, extract the abbreviation
        state_abbr = None
        if state_str:
            state_abbr, _ = extract_state_detailed(state_str, strict=True)
            
        if email in email_map:
            if not email_map[email]['state'] and state_abbr:
                email_map[email]['state'] = state_abbr
            if not email_map[email]['company'] and comp:
                email_map[email]['company'] = comp
        else:
            email_map[email] = {
                'location': None,
                'state': state_abbr,
                'company': comp
            }
            
    print(f"Total unique emails loaded: {len(email_map)}", flush=True)
    
    session = SessionLocal()
    
    # Query all recruiters missing state OR location
    print("Querying recruiters...", flush=True)
    recruiters = session.execute(text("SELECT recruiter_id, email, location, state FROM recruiters WHERE state IS NULL OR location IS NULL")).mappings().all()
    
    updates = []
    
    print("Matching...", flush=True)
    for r in recruiters:
        email = r['email']
        if not email:
            continue
        email = email.strip().lower()
        
        if email in email_map:
            data = email_map[email]
            
            new_loc = data['location'] if not r['location'] else None
            new_state = data['state'] if not r['state'] else None
            
            # If we extracted a location from master sheet, also try to infer state from it right now!
            if new_loc and not new_state and not r['state']:
                inferred_state, _ = extract_state_detailed(new_loc, strict=False) # OK to use non-strict on explicit location strings!
                if inferred_state:
                    new_state = inferred_state
                    
            if new_loc or new_state:
                updates.append({
                    'id': r['recruiter_id'],
                    'loc': new_loc or r['location'],
                    'st': new_state or r['state']
                })
                
    print(f"Found {len(updates)} matches to backfill!", flush=True)
    
    if updates:
        batch_size = 1000
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            session.execute(text("""
                UPDATE recruiters 
                SET location = :loc,
                    state = :st
                WHERE recruiter_id = :id
            """), batch)
        session.commit()
        print("Backfill complete!", flush=True)
        
    session.close()

if __name__ == '__main__':
    run_recovery()
