import os
import sys
import re
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.phone_normalizer import format_us_phone

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

BAD_NAME_PATTERNS = [
    r"^n/a$", r"^na$", r"^none$", r"^null$", r"^unknown$", r"^placeholder$", r"^test$", r"^recruiter$", r"^user$", r"^n$"
]

def clean_name(name):
    if not name:
        return None
    name_strip = name.strip()
    
    # Check if name is placeholder
    for pattern in BAD_NAME_PATTERNS:
        if re.match(pattern, name_strip.lower()):
            return None
            
    # Check if name contains email or url
    if "@" in name_strip or "http" in name_strip or ".com" in name_strip:
        return None
        
    # Remove excessive symbols/numbers from name
    cleaned = re.sub(r"[0-9#$^*+_={}|\[\]\\:;<>?~]", "", name_strip)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    if len(cleaned) < 2:
        return None
        
    # Normalize casing if all upper or all lower
    if cleaned.isupper() or cleaned.islower():
        cleaned = cleaned.title()
        
    return cleaned

def clean_email(email):
    if not email:
        return None
    email_clean = email.strip().lower()
    
    # Fix double @ symbols or trailing dots
    email_clean = re.sub(r"@+", "@", email_clean)
    email_clean = email_clean.rstrip(".")
    
    # Remove spaces
    email_clean = re.sub(r"\s+", "", email_clean)
    
    # Check if it looks like a valid email
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
        return None
        
    # Check if it's a known bad/placeholder email
    if "missing.local" in email_clean or "placeholder" in email_clean:
        return None
        
    return email_clean

def clean_state(state):
    if not state:
        return None
    state_clean = state.strip().upper()
    if state_clean in US_STATES:
        return state_clean
    return None

def main():
    print("=== STARTING COMPREHENSIVE DB CLEANSE ===")
    
    # STEP 1: Identify and rename duplicate emails to free up unique slots
    print("Step 1: Resolving unique constraint duplicates...")
    db = SessionLocal()
    try:
        recruiters = db.query(Recruiter).all()
        print(f"Loaded {len(recruiters)} recruiters for deduplication.")
        
        email_owners = {}
        disabled_bad_records = 0
        step1_updates = 0
        
        for r in recruiters:
            if r.email:
                email_clean = r.email.strip().lower()
                if email_clean in email_owners:
                    r.is_active = False
                    orig_email = r.email
                    r.email = f"{orig_email}.dup.{r.recruiter_id}"
                    disabled_bad_records += 1
                    step1_updates += 1
                else:
                    email_owners[email_clean] = r.recruiter_id
                    
        if step1_updates > 0:
            db.commit()
            print(f"Committed {step1_updates} duplicate email renames to database.")
        else:
            print("No duplicate email conflicts found.")
            db.rollback()
    except Exception as e:
        db.rollback()
        print(f"Step 1 failed: {e}")
        db.close()
        sys.exit(1)
    finally:
        db.close()

    # STEP 2: Perform normalizations and general cleansing
    print("\nStep 2: Normalizing names, phone numbers, states, and emails...")
    db = SessionLocal()
    try:
        # Reload to get fresh states with renamed emails
        recruiters = db.query(Recruiter).all()
        
        # Build fresh email owners map (guaranteed unique now)
        email_owners = {}
        for r in recruiters:
            if r.email:
                email_owners[r.email.strip().lower()] = r.recruiter_id
                
        updated_count = 0
        
        for r in recruiters:
            changes = {}
            
            if r.email and ".dup." in r.email:
                continue
                
            # Clean Name
            c_name = clean_name(r.recruiter_name)
            if c_name is None:
                c_name = "[Invalid Name]"
                
            if c_name != r.recruiter_name:
                changes["recruiter_name"] = (r.recruiter_name, c_name)
                r.recruiter_name = c_name
                
            # Clean Email
            c_email = clean_email(r.email)
            if c_email is not None:
                if c_email in email_owners and email_owners[c_email] != r.recruiter_id:
                    # De-activate and rename if a conflict is dynamically introduced
                    r.is_active = False
                    r.email = f"{r.email}.dup.{r.recruiter_id}"
                    disabled_bad_records += 1
                    changes["is_active"] = (True, False)
                    changes["email_dup"] = (r.email, r.email)
                else:
                    if r.email:
                        old_clean = r.email.strip().lower()
                        if old_clean in email_owners and email_owners[old_clean] == r.recruiter_id:
                            del email_owners[old_clean]
                    email_owners[c_email] = r.recruiter_id
                    if c_email != r.email:
                        changes["email"] = (r.email, c_email)
                        r.email = c_email
            
            # Clean State
            if r.state:
                c_state = clean_state(r.state)
                if c_state != r.state:
                    changes["state"] = (r.state, c_state)
                    r.state = c_state
                    
            # Clean primary phone
            if r.phone:
                c_phone = format_us_phone(r.phone)
                if c_phone != r.phone:
                    changes["phone"] = (r.phone, c_phone)
                    r.phone = c_phone

            # Clean secondary phone
            if r.phone2:
                c_phone2 = format_us_phone(r.phone2)
                if c_phone2 != r.phone2:
                    changes["phone2"] = (r.phone2, c_phone2)
                    r.phone2 = c_phone2
            
            # Soft disable extremely low-quality profiles
            if r.recruiter_name == "[Invalid Name]" or not r.email or "missing.local" in r.email:
                if r.is_active:
                    r.is_active = False
                    disabled_bad_records += 1
                    changes["is_active"] = (True, False)
            
            if changes:
                updated_count += 1
                
        db.commit()
        print(f"Sanitization complete! Updated {updated_count} records. Soft-disabled {disabled_bad_records} duplicate/invalid profiles.")
    except Exception as e:
        db.rollback()
        print(f"Step 2 failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
