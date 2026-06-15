import pandas as pd
from sqlalchemy import text
from app.database import SessionLocal
from app.utils.state_mapper import extract_state_detailed

def run_final_sheet_recovery():
    print("Loading final updated sheet...", flush=True)
    df = pd.read_excel('C:/Users/User/Desktop/final updated sheet.xlsx', dtype=str)
    
    print("Parsing rows...", flush=True)
    updates = []
    
    session = SessionLocal()
    
    # We only care about emails that currently have NO state in the DB
    missing_emails_query = session.execute(text("SELECT email FROM recruiters WHERE state IS NULL")).fetchall()
    missing_emails = {row[0].strip().lower() for row in missing_emails_query if row[0]}
    
    email_to_state = {}
    
    for _, row in df.iterrows():
        # Find email in the row
        row_vals = [str(x).strip() for x in row.values if pd.notna(x)]
        email = next((x.lower() for x in row_vals if '@' in x and ' ' not in x), None)
        
        if not email or email not in missing_emails:
            continue
            
        # Combine everything else into a massive string
        context = " ".join(row_vals)
        state_abbr, _ = extract_state_detailed(context, strict=True)
        
        if state_abbr:
            email_to_state[email] = state_abbr

    print(f"Recovered {len(email_to_state)} states from chaotic final sheet!", flush=True)
    
    # Execute updates
    if email_to_state:
        batch = [{'email': e, 'st': s} for e, s in email_to_state.items()]
        for i in range(0, len(batch), 1000):
            session.execute(text("""
                UPDATE recruiters 
                SET state = :st, state_source = 'final_updated_sheet_raw_parse', state_confidence = 'high'
                WHERE email = :email AND state IS NULL
            """), batch[i:i+1000])
        session.commit()
        print("Database updated!", flush=True)
        
    session.close()

if __name__ == '__main__':
    run_final_sheet_recovery()
