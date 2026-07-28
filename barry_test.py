import pandas as pd
import os
import sys

sys.path.append(r"C:\TalentOpsAI\backend")
from intelligent_importer import process_file, smart_merge, DB_URL

print("=== BARRY PROTOCOL: PASS 1 ===")

# Create a malicious test dataset
data = [
    # Edge Case 1: All blank
    ["", "", ""],
    # Edge Case 2: Only whitespace
    ["   ", "  \xa0 ", "   \t "],
    # Edge Case 3: Missing name but valid email
    [None, "ghost@example.com", None],
    # Edge Case 4: Invalid email format
    ["Bad Email Guy", "not_an_email.com", "555-1234"],
    # Edge Case 5: Extremely long names
    ["A" * 500, "long@example.com", "1234567890"],
    # Edge Case 6: Duplicate names with varying capitalization
    ["John Doe", "john1@ex.com", "1112223333"],
    ["JOHN DOE", "john2@ex.com", "4445556666"],
    # Edge Case 7: Phone number with letters
    ["Phone Guy", "phone@ex.com", "1-800-RECRUIT"],
    # Edge Case 8: Duplicate emails for different names (Should group by email!)
    ["Alice", "shared@ex.com", "111"],
    ["Bob", "shared@ex.com", "222"],
]

df = pd.DataFrame(data, columns=['Name', 'Email', 'Phone'])
test_file = r"C:\TalentOpsAI\malicious_test.xlsx"
df.to_excel(test_file, index=False, header=False)

try:
    print("\n[BARRY] Running Stage 1 & 2 (Process File)...")
    profiles = process_file(test_file)
    
    # Assertions
    print(f"\n[BARRY] Checking output profile count... (Expected ~6 valid profiles, got {len(profiles)})")
    for key, p in profiles.items():
        print(f"Profile Key '{key}': Name='{p['name']}', Emails={p['emails']}, Phones={p['phones']}")
        
    print("\n[BARRY] Running Stage 5 & 6 (Smart Merge Dry-Run)...")
    smart_merge(profiles, dry_run=True)
    
except Exception as e:
    print(f"\n[BARRY FATAL ERROR]: Pipeline crashed during processing: {e}")

print("\n[BARRY] Verifying Storage Kill-Switch Requirement...")
storage_check_exists = os.path.exists(r"C:\TalentOpsAI\backend\app\services\storage_limit_service.py")
if not storage_check_exists:
    print("[BARRY FATAL ERROR]: Business Requirement Failed. The 75% Storage Limit Kill-Switch does not exist!")

print("\n=== BARRY PASS 1 COMPLETE ===")
