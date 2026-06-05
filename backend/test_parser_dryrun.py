"""
Dry-run test of the adaptive parser.
NO database writes. Read-only analysis.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, "C:/TalentOpsAI/backend")

from app.services.adaptive_parser import parse_file

UPLOAD_DIR = "C:/TalentOpsAI/backend/uploads"

def test_file(filepath, max_rows=50):
    """Test parsing a file and print results."""
    print(f"\n{'='*80}")
    print(f"FILE: {os.path.basename(filepath)} ({os.path.getsize(filepath):,} bytes)")
    print(f"{'='*80}")
    
    result = parse_file(filepath, max_rows_per_sheet=max_rows)
    
    if result.errors:
        print(f"  ERRORS: {result.errors}")
        return
    
    print(f"  Sheets: {result.sheet_count} -> {result.sheet_names}")
    
    for sheet in result.sheets:
        print(f"\n  --- Sheet: '{sheet.sheet_name}' ---")
        print(f"    Format: {sheet.detected_format} (confidence: {sheet.format_confidence})")
        print(f"    Has headers: {sheet.has_headers}")
        print(f"    Headers: {sheet.headers}")
        print(f"    Total rows: {sheet.total_rows:,}")
        print(f"    Data rows (non-blank): {sheet.data_rows:,}")
        print(f"    Blank rows: {sheet.blank_rows:,}")
        print(f"    With email: {sheet.rows_with_email:,}")
        print(f"    Without email: {sheet.rows_without_email:,}")
        
        mapping = sheet.column_mapping
        print(f"    Mapping method: {mapping.detection_method}")
        print(f"    name -> '{mapping.name}'")
        print(f"    email -> '{mapping.email}'")
        print(f"    company -> '{mapping.company}'")
        print(f"    state -> '{mapping.state}'")
        print(f"    location -> '{mapping.location}'")
        print(f"    phone -> '{mapping.phone}'")
        print(f"    title -> '{mapping.title}'")
        print(f"    unmapped: {mapping.unmapped_columns}")
        
        # Show first 3 parsed rows
        for i, row in enumerate(sheet.parsed_rows[:3]):
            print(f"\n    Row {row.row_index}:")
            print(f"      Name: {row.name}")
            print(f"      Email: {row.email}")
            print(f"      Company: {row.company}")
            print(f"      State: {row.state}")
            print(f"      Location: {row.location}")
            print(f"      Phone: {row.phone}")
            print(f"      Title: {row.title}")
            print(f"      Needs review: {row.needs_review} {row.review_reasons}")
            print(f"      Metadata: {row.metadata}")
            print(f"      Raw: {row.raw_data}")
        
        # Count review reasons
        reasons = {}
        for r in sheet.parsed_rows:
            for reason in r.review_reasons:
                reasons[reason] = reasons.get(reason, 0) + 1
        if reasons:
            print(f"\n    Review reasons summary: {reasons}")

if __name__ == "__main__":
    files = sorted([f for f in os.listdir(UPLOAD_DIR) if f.endswith((".xlsx", ".csv"))])
    
    # Test the master file (first 50 rows per sheet)
    master = "202f1fec-7f3a-4916-a5ef-db0ab4ae8bea.xlsx"
    if master in files:
        test_file(os.path.join(UPLOAD_DIR, master), max_rows=50)
    
    # Test the CSV
    csv_file = "7b50a76b-1097-4dd8-8645-ce32bb9801e4.csv"
    if csv_file in files:
        test_file(os.path.join(UPLOAD_DIR, csv_file), max_rows=50)
    
    print("\n\nDry-run complete. No data was written to any database.")
