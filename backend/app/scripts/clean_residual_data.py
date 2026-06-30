import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter

def is_valid_email_value(val):
    if not val:
        return False
    val = val.strip().lower()
    if val in ("0", "0.0", "1", "1.0", "false", "true", "null", "none"):
        return False
    if "@" not in val:
        return False
    return True

def is_valid_phone_value(val):
    if not val:
        return False
    val = val.strip().lower()
    if val in ("0", "0.0", "1", "1.0", "false", "true", "null", "none"):
        return False
    # Strip non-digits to see if we have actual numbers
    digits = re.sub(r"\D+", "", val)
    if len(digits) < 7:
        return False
    return True

def clean_phone_prefix(val):
    if not val:
        return None
    val = val.strip()
    # If it starts with "1." and is followed by a number (like "1.408-448-5992" from Excel parsing export)
    if val.startswith("1.") and len(val) > 10:
        val = val[2:]
    return val

def main():
    db = SessionLocal()
    try:
        recruiters = db.query(Recruiter).all()
        print(f"Inspecting {len(recruiters)} recruiters for residual junk data...")
        
        junk_emails_cleaned = 0
        junk_phones_cleaned = 0
        disabled_linkedin_placeholders = 0
        cleaned_phone_prefixes = 0
        
        for r in recruiters:
            modified = False
            
            # 1. Clean email fields containing junk (0, false, 1.0, etc.)
            for field in ("email", "email2", "email3", "email4"):
                val = getattr(r, field)
                if val:
                    if not is_valid_email_value(val):
                        # email is NOT NULL, so if it's the primary email, we replace with missing.local format instead of setting to None
                        if field == "email":
                            new_email = f"no-email-{r.recruiter_id}@missing.local"
                            setattr(r, field, new_email)
                        else:
                            setattr(r, field, None)
                        junk_emails_cleaned += 1
                        modified = True
            
            # 2. Clean phone fields
            for field in ("phone", "phone2", "phone3", "phone4"):
                val = getattr(r, field)
                if val:
                    # Clean prefixes like "1." from excel float parses
                    cleaned_val = clean_phone_prefix(val)
                    if cleaned_val != val:
                        setattr(r, field, cleaned_val)
                        val = cleaned_val
                        cleaned_phone_prefixes += 1
                        modified = True
                        
                    if not is_valid_phone_value(val):
                        setattr(r, field, None)
                        junk_phones_cleaned += 1
                        modified = True
            
            # 3. Handle recruiter names containing "linkedin"
            if r.recruiter_name and "linkedin" in r.recruiter_name.lower():
                if r.is_active:
                    r.is_active = False
                    disabled_linkedin_placeholders += 1
                    modified = True
                    
        db.commit()
        print("Junk data cleanup complete!")
        print(f"Junk emails cleaned: {junk_emails_cleaned}")
        print(f"Junk phones cleaned: {junk_phones_cleaned}")
        print(f"Phone prefixes cleaned: {cleaned_phone_prefixes}")
        print(f"LinkedIn placeholder profiles disabled: {disabled_linkedin_placeholders}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
