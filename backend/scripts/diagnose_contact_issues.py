import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.database import SessionLocal
from app.models.models import Recruiter
from sqlalchemy import func

def run_diagnostics():
    db = SessionLocal()
    print('=== DEEP DIAGNOSTIC OF SCRAPING & CONTACT ARTIFACTS ===')

    # 1. Title contains 'LinkedIn' or '|' or name prefix
    linkedin_in_title = db.query(Recruiter).filter(Recruiter.title != None, (Recruiter.title.ilike('%linkedin%') | Recruiter.title.contains(' | '))).count()
    print(f'1. Title field contains "LinkedIn" or " | " SERP artifacts: {linkedin_in_title}')

    # 2. Recruiter Name contains ' - ' or ' | ' or ' (' or 'LinkedIn'
    name_serp_artifacts = db.query(Recruiter).filter(Recruiter.recruiter_name != None, (Recruiter.recruiter_name.ilike('%linkedin%') | Recruiter.recruiter_name.contains(' - ') | Recruiter.recruiter_name.contains(' | ') | Recruiter.recruiter_name.contains(' ('))).count()
    print(f'2. Recruiter Name contains SERP artifacts (- / | / ( / LinkedIn): {name_serp_artifacts}')

    # 3. Bad/Junk Phones
    junk_phones = db.query(Recruiter).filter(Recruiter.phone != None, Recruiter.phone.in_(['000-000-0000', '123-456-7890', '999-999-9999', 'none', 'nan', 'null', 'N/A', 'n/a', '0', '1234567890']) | (func.length(Recruiter.phone) < 7)).count()
    print(f'3. Junk or short exact phones (< 7 chars or 000-000-0000 etc): {junk_phones}')

    # 4. Malformed emails
    bad_emails = db.query(Recruiter).filter(~Recruiter.email.contains('missing.local'), (Recruiter.email.ilike('mailto:%') | Recruiter.email.like('%@%@%') | ~Recruiter.email.contains('.'))).count()
    print(f'4. Malformed emails (mailto:, multiple @, or no TLD dot): {bad_emails}')

    # 5. Generic/Title words in recruiter_name (where recruiter_name equals 'Recruiter', 'Talent Acquisition', etc.)
    generic_names = db.query(Recruiter).filter(func.lower(Recruiter.recruiter_name).in_(['recruiter', 'talent acquisition', 'technical recruiter', 'hr manager', 'hr', 'human resources', 'staffing specialist', 'contact', 'info', 'support', 'n/a', 'nan', 'null', 'admin', 'team'])).count()
    print(f'5. Exact generic title/placeholder words as recruiter_name: {generic_names}')

    # 6. Check how many records have ALL CAPS names (> 3 chars) across all 327,319
    print('Checking ALL CAPS and lowercase names across all 327,319 records...')
    count_caps = 0
    count_lower = 0
    names = db.query(Recruiter.recruiter_id, Recruiter.recruiter_name).filter(Recruiter.recruiter_name != None, func.length(Recruiter.recruiter_name) > 3).all()
    for id_, name in names:
        if name.isupper() and any(c.isalpha() for c in name):
            count_caps += 1
        elif name.islower() and any(c.isalpha() for c in name):
            count_lower += 1
    print(f'6. ALL CAPS names across DB: {count_caps}')
    print(f'7. All lowercase names across DB: {count_lower}')

    db.close()

if __name__ == '__main__':
    run_diagnostics()
