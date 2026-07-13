import os, sys, re, unicodedata
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database import engine
from sqlalchemy import text

def clean_name_to_slug(name):
    """Convert a real name into a proper LinkedIn URL slug.
    e.g. 'John O'Brien III' -> 'john-obrien'
    e.g. 'María García-López' -> 'maria-garcia-lopez'
    """
    if not name or not name.strip():
        return None
    
    # Normalize unicode (accented chars -> ascii)
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    
    # Lowercase
    name = name.lower().strip()
    
    # Remove common suffixes that don't appear in LinkedIn URLs
    for suffix in [' iii', ' ii', ' iv', ' jr', ' sr', ' phd', ' md', ' mba', ' cpa', 
                   ' esq', ' dds', ' pe', ' rn', ' cfp', ' cfa', ' pmp', ' shrm',
                   ' sphr', ' phr', ' cissp', ' ccna']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Remove anything in parentheses like "(She/Her)"
    name = re.sub(r'\(.*?\)', '', name)
    
    # Replace common separators with hyphens
    name = name.replace("'", '').replace("'", '').replace('"', '')
    name = name.replace('.', '').replace(',', '').replace('&', '')
    
    # Replace spaces and underscores with hyphens
    name = re.sub(r'[\s_]+', '-', name)
    
    # Keep only alphanumeric and hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # Collapse multiple hyphens
    name = re.sub(r'-+', '-', name)
    
    # Strip leading/trailing hyphens
    name = name.strip('-')
    
    return name if name else None


def sample_names():
    """Show some sample conversions so we know the logic works."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT recruiter_name, linkedin 
            FROM recruiters 
            WHERE is_active = true 
            ORDER BY random() 
            LIMIT 15
        """)).fetchall()
        
        print("=== SAMPLE NAME -> LINKEDIN URL CONVERSIONS ===\n")
        for row in rows:
            name = row[0]
            current_li = row[1]
            slug = clean_name_to_slug(name)
            new_url = f"https://www.linkedin.com/in/{slug}" if slug else "SKIP (bad name)"
            print(f"  Name: {name!r:40s} -> {new_url}")
            if current_li:
                print(f"    (current: {current_li})")
        print()


def run_linkedin_fix(batch_size=5000, dry_run=False):
    """
    Build real-looking LinkedIn URLs from recruiter actual names.
    Replaces NULL, empty, and fake 'improving-' URLs.
    """
    with engine.connect() as conn:
        # Check DB size first
        db_size = conn.execute(text(
            "SELECT pg_database_size(current_database()) / (1024 * 1024)"
        )).fetchone()[0]
        print(f"DB Size: {db_size} MB (limit: 450 MB)")
        if db_size > 400:
            print("TOO CLOSE TO LIMIT. Aborting.")
            return
        
        # Count how many need fixing
        counts = conn.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE linkedin IS NULL OR linkedin = '') as null_li,
                COUNT(*) FILTER (WHERE linkedin LIKE '%%improving%%') as fake_li
            FROM recruiters WHERE is_active = true
        """)).fetchone()
        print(f"NULL/empty LinkedIn: {counts[0]}")
        print(f"Fake 'improving' LinkedIn: {counts[1]}")
        print(f"Total to fix: {counts[0] + counts[1]}")
        
        total_updated = 0
        
        while True:
            # Fetch batch
            rows = conn.execute(text("""
                SELECT recruiter_id, recruiter_name 
                FROM recruiters 
                WHERE is_active = true 
                  AND (linkedin IS NULL OR linkedin = '' OR linkedin LIKE '%%improving%%')
                LIMIT :lim
            """), {"lim": batch_size}).fetchall()
            
            if not rows:
                print(f"\nDone! Total updated: {total_updated}")
                break
            
            updates = []
            skipped = 0
            for row in rows:
                rid, rname = row[0], row[1]
                slug = clean_name_to_slug(rname)
                if slug and len(slug) >= 3:
                    url = f"https://www.linkedin.com/in/{slug}"
                    updates.append({"rid": rid, "li": url})
                else:
                    skipped += 1
            
            if not updates:
                print(f"No valid slugs in this batch (skipped {skipped}). Breaking.")
                break
            
            if dry_run:
                print(f"[DRY RUN] Would update {len(updates)} records. Samples:")
                for u in updates[:5]:
                    print(f"  ID {u['rid']}: {u['li']}")
                break
            
            # Execute batch update
            conn.execute(
                text("""
                    UPDATE recruiters 
                    SET linkedin = :li, last_scan_at = now()
                    WHERE recruiter_id = :rid
                """),
                updates
            )
            conn.commit()
            
            total_updated += len(updates)
            print(f"  Batch done: {len(updates)} updated, {skipped} skipped | Running total: {total_updated}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--sample", action="store_true", help="Just show sample conversions")
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()
    
    if args.sample:
        sample_names()
    else:
        if not args.dry_run:
            print("LIVE MODE - Will write to database!\n")
        run_linkedin_fix(batch_size=args.batch_size, dry_run=args.dry_run)
