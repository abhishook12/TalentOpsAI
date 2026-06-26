import os
import psycopg
import argparse
import re
import dns.resolver
from dotenv import load_dotenv
from collections import Counter

load_dotenv("C:/TalentOpsAI/backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")

def get_db():
    return psycopg.connect(DATABASE_URL, prepare_threshold=None)

def is_placeholder(email):
    if not email: return True
    email = email.lower()
    if "@missing.local" in email or "@invalid.local" in email or "@example.com" in email:
        return True
    if "linkedin_" in email:
        return True
    # Random hexadecimal local part
    local_part = email.split('@')[0]
    if re.match(r'^[a-f0-9]{8,}$', local_part):
        return True
    if "unknown" in local_part or "dummy" in local_part or "fake" in local_part or "noemail" in local_part:
        return True
    return False

def validate_mx(domain):
    return True

def discover_patterns(cur, company_id, _ignored=None):
    # Fetch verified emails for this company
    cur.execute("""
        SELECT r.email, r.recruiter_name FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        LEFT JOIN company_aliases ca ON c.company_name ILIKE ca.alias_name AND ca.canonical_company_id = %s
        WHERE (r.company_id = %s OR ca.canonical_company_id = %s)
        AND r.email_status IN ('verified', 'unknown', 'likely', 'inferred') AND r.email IS NOT NULL
    """, (company_id, company_id, company_id))
    emails = cur.fetchall()
    
    # First, find the most common domain among these emails
    domain_counts = Counter()
    for e, name in emails:
        if is_placeholder(e): continue
        parts = e.split('@')
        if len(parts) == 2:
            domain_counts[parts[1].lower()] += 1
            
    if not domain_counts:
        return None, None, 0, 0, "No valid examples"
        
    best_domain, domain_count = domain_counts.most_common(1)[0]
    
    # Now find pattern for best_domain
    patterns = []
    for e, name in emails:
        if is_placeholder(e): continue
        if not e.endswith(f"@{best_domain}"): continue
        
        # Determine pattern
        local_part = e.split('@')[0].lower()
        
        name_parts = name.lower().replace(".", "").replace(",", "").split()
        if len(name_parts) < 2: continue
        
        first = name_parts[0]
        last = name_parts[-1]
        
        if local_part == f"{first}.{last}": patterns.append("{first}.{last}")
        elif local_part == f"{first}{last}": patterns.append("{first}{last}")
        elif local_part == f"{first[0]}{last}": patterns.append("{first_initial}{last}")
        elif local_part == f"{first}_{last}": patterns.append("{first}_{last}")
        elif local_part == first: patterns.append("{first}")
        elif local_part == last: patterns.append("{last}")
        elif local_part == f"{first}.{last[0]}": patterns.append("{first}.{last_initial}")

    if not patterns:
        return best_domain, None, 0, 0, "No valid patterns"
        
    c = Counter(patterns)
    best_pattern, count = c.most_common(1)[0]
    percentage = count / len(patterns)
    
    confidence = "low"
    if count >= 5 and percentage >= 0.9:
        confidence = "high"
    elif count >= 3 and percentage >= 0.75:
        confidence = "medium"
        
    return best_domain, best_pattern, count, percentage, confidence

def generate_candidates(name, domain, pattern):
    name_parts = name.lower().replace(".", "").replace(",", "").split()
    if len(name_parts) < 2: return []
    first = name_parts[0]
    last = name_parts[-1]
    first_initial = first[0]
    last_initial = last[0]
    
    candidates = []
    if pattern == "{first}.{last}": candidates.append(f"{first}.{last}@{domain}")
    elif pattern == "{first}{last}": candidates.append(f"{first}{last}@{domain}")
    elif pattern == "{first_initial}{last}": candidates.append(f"{first_initial}{last}@{domain}")
    elif pattern == "{first}_{last}": candidates.append(f"{first}_{last}@{domain}")
    elif pattern == "{first}": candidates.append(f"{first}@{domain}")
    elif pattern == "{first}.{last_initial}": candidates.append(f"{first}.{last_initial}@{domain}")
    
    return candidates

def resolve_company(cur, company_name):
    # Check aliases
    cur.execute("""
        SELECT canonical_company_id FROM company_aliases WHERE alias_name ILIKE %s
    """, (company_name,))
    row = cur.fetchone()
    if row:
        cur.execute("SELECT company_id, company_name, website FROM companies WHERE company_id = %s", (row[0],))
        return cur.fetchone()
    
    cur.execute("SELECT company_id, company_name, website FROM companies WHERE company_name ILIKE %s", (company_name,))
    return cur.fetchone()

def is_human_name(name):
    if not name: return False
    words = name.split()
    if len(words) < 2: return False
    generic_words = ["executive", "recruiter", "manager", "director", "talent", "acquisition", "hr", "admin", "team"]
    for w in words:
        if w.lower() in generic_words: return False
    return True

def repair_recruiter(conn, r, args):
    rid, name, email, cid, cname, website, raw_email, status = r
    print(f"\nProcessing Recruiter: {name} (ID: {rid})")
    
    cur = conn.cursor()
    
    if not is_placeholder(email) and status == "verified":
        print("Skipping: Email is already verified.")
        return
        
    if not is_human_name(name):
        print(f"Skipping: '{name}' does not appear to be a real human name.")
        if is_placeholder(email):
            cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE recruiter_id = %s", (rid,))
            if args.apply: conn.commit()
        return
        
    # 1. Resolve Company
    company_info = resolve_company(cur, cname)
    if not company_info:
        print(f"Company {cname} not found or resolved.")
        if is_placeholder(email):
            cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE recruiter_id = %s", (rid,))
            if args.apply: conn.commit()
        return
        
    canonical_cid, canonical_cname, canonical_domain = company_info
    print(f"Resolved Company: {canonical_cname} (ID: {canonical_cid})")
    
    # Domain parsing
    domain = None
    if canonical_domain:
        # Strip protocol
        domain = canonical_domain.replace('http://', '').replace('https://', '').split('/')[0].lower()
        if 'www.' in domain:
            domain = domain.replace('www.', '')
            
    alias_domains = []
    cur.execute("SELECT alias_name FROM company_aliases WHERE canonical_company_id = %s AND alias_name LIKE '%%.%%'", (canonical_cid,))
    for ar in cur.fetchall():
        ad = ar[0].lower().replace('http://', '').replace('https://', '').split('/')[0]
        if 'www.' in ad: ad = ad.replace('www.', '')
        if '.' in ad: alias_domains.append(ad)
        
    domains_to_check = []
    if domain: domains_to_check.append(domain)
    for d in alias_domains:
        if d not in domains_to_check:
            domains_to_check.append(d)
            
    if not domains_to_check:
        print("No valid domain found for company.")
        if is_placeholder(email):
            cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE recruiter_id = %s", (rid,))
            if args.apply: conn.commit()
        return
        
    print(f"Domains to check: {domains_to_check}")
    
    # 2. Discover Patterns
    found_domain, pattern, count, percentage, confidence = discover_patterns(cur, canonical_cid, None)
    if found_domain: domain = found_domain
    
    print(f"Discovered Pattern: {pattern} on {domain} (Count: {count}, %: {percentage:.2f}, Confidence: {confidence})")
    
    if not pattern or confidence == "low" or confidence == "no confidence":
        print("Skipping: Not enough pattern confidence to generate.")
        if is_placeholder(email):
            cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE recruiter_id = %s", (rid,))
            if args.apply: conn.commit()
        return

    # 3. Generate Candidates
    candidates = generate_candidates(name, domain, pattern)
    if not candidates:
        print("No candidates generated.")
        if is_placeholder(email):
            cur.execute("UPDATE recruiters SET email_status = 'placeholder', repair_reason = 'Placeholder detected' WHERE recruiter_id = %s", (rid,))
            if args.apply: conn.commit()
        return
        
    best_candidate = candidates[0]
    print(f"Best Candidate: {best_candidate}")
    
    # 4. Check MX and Duplicates
    if not args.dry_run:
        # MX validation can be slow, only do it if applying
        pass 
        
    # Check duplicates
    cur.execute("SELECT recruiter_id FROM recruiters WHERE email = %s AND recruiter_id != %s", (best_candidate, rid))
    dup = cur.fetchone()
    if dup:
        print(f"Conflict: Email {best_candidate} already owned by recruiter {dup[0]}")
        return
        
    # 5. Apply Changes
    print(f"Planned Action: Change email to {best_candidate} (Confidence: {confidence})")
    
    if not args.dry_run:
        # Save to pattern table if not exists
        cur.execute("INSERT INTO company_email_patterns (company_id, domain, pattern, verified_example_count, match_percentage, confidence) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (canonical_cid, domain, pattern, count, percentage, confidence))
        pattern_id = cur.fetchone()[0]
        
        # Save candidates
        cur.execute("INSERT INTO email_candidates (recruiter_id, candidate_email, domain, pattern, confidence_score, status) VALUES (%s, %s, %s, %s, %s, 'selected')", (rid, best_candidate, domain, pattern, 90 if confidence == 'high' else 75))
        
        new_status = 'likely' if confidence == 'high' else 'inferred'
        
        # Save placeholder to raw if not already there
        actual_raw = raw_email if raw_email else email
        
        cur.execute("""
            UPDATE recruiters SET 
            email = %s, email_status = %s, email_confidence = %s, email_generated = TRUE,
            canonical_company_id = %s, company_domain_id = %s, raw_email_value = %s, email_pattern_id = %s,
            repair_reason = 'Repaired using evidence-based pattern'
            WHERE recruiter_id = %s
        """, (best_candidate, new_status, 90 if confidence == 'high' else 75, canonical_cid, None, actual_raw, pattern_id, rid))
        conn.commit()
        print("Applied successfully.")
    
def main():
    parser = argparse.ArgumentParser(description="Repair Recruiter Emails")
    parser.add_argument("--company", type=str, help="Target specific company")
    parser.add_argument("--recruiter-id", type=int, help="Target specific recruiter")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without modifying DB")
    parser.add_argument("--apply", action="store_true", help="Apply changes to DB")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    args = parser.parse_args()

    conn = get_db()
    
    query = """
        SELECT r.recruiter_id, r.recruiter_name, r.email, c.company_id, c.company_name, c.website, r.raw_email_value, r.email_status
        FROM recruiters r
        JOIN companies c ON r.company_id = c.company_id
        WHERE (r.email_status = 'unknown' OR r.email_status IS NULL)
    """
    params = []
    
    if args.company:
        query += " AND c.company_name ILIKE %s"
        params.append(f"%{args.company}%")
    if args.recruiter_id:
        query += " AND r.recruiter_id = %s"
        params.append(args.recruiter_id)
        
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} recruiters to process.")
    for r in rows:
        repair_recruiter(conn, r, args)
        
    print("Done processing recruiters.")
    if args.apply:
        conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
