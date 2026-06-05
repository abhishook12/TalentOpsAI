"""Self-test for dedup_engine – run with: python test_dedup_engine.py"""

import sys, os, json

# Add project root so we can import the module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.dedup_engine import (
    deduplicate_and_enrich,
    normalize_email,
    normalize_name,
    normalize_company,
)

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  —  {detail}")


# ── Normalization helpers ─────────────────────────────────────────────────

print("\n═══ Normalization helpers ═══")

check("normalize_email basic", normalize_email("  Alice@EXAMPLE.com  ") == "alice@example.com")
check("normalize_email None",  normalize_email(None) == "")
check("normalize_name collapse", normalize_name("  John   Doe  ") == "john doe")
check("normalize_company strips suffix", normalize_company("Acme Corp.") == "acme")
check("normalize_company LLC", normalize_company("Widget LLC") == "widget")
check("normalize_company Inc", normalize_company("GlobalTech, Inc.") == "globaltech")
check("normalize_company passthrough", normalize_company("OpenAI") == "openai")


# ── Test 1: Same email, different states → MERGE ─────────────────────────

print("\n═══ Test 1: Same email – definite merge ═══")

rows_email = [
    {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "company": "Acme Corp",
        "state": "CA",
        "location": "San Francisco",
        "phone": "555-0001",
        "title": "Recruiter",
        "specialization": "",
        "notes": "",
        "raw_data": "row1-raw",
        "source_sheet": "Sheet1",
        "source_file": "file1.xlsx",
        "row_index": 2,
    },
    {
        "name": "Alice Smith",
        "email": "Alice@Example.com",     # same email, different casing
        "company": "Acme Corp.",
        "state": "NY",                    # different state
        "location": "",                   # empty – should NOT overwrite primary
        "phone": "555-0002",
        "title": "Senior Recruiter",
        "specialization": "Tech",         # fills empty field in primary
        "notes": "Met at conference",
        "raw_data": "row2-raw",
        "source_sheet": "Sheet2",
        "source_file": "file2.xlsx",
        "row_index": 5,
    },
]

unique, report = deduplicate_and_enrich(rows_email)

check("produces 1 unique profile", len(unique) == 1, f"got {len(unique)}")
p = unique[0]
check("primary state kept (CA)",   p["state"] == "CA",        f"got {p['state']}")
check("specialization back-filled", p["specialization"] == "Tech", f"got {p.get('specialization')}")
check("primary location kept",     p["location"] == "San Francisco")
check("all_emails has both variants",
      set(p["metadata_json"]["all_emails"]) == {"alice@example.com", "Alice@Example.com"},
      f"got {p['metadata_json']['all_emails']}")
check("alternate_entries has 1 entry", len(p["metadata_json"]["alternate_entries"]) == 1)
check("report has merge action",
      any(r["action"] == "merged" for r in report))
check("no possible_duplicate flag", p.get("possible_duplicate") is not True)


# ── Test 2: Same name + company, different email → FLAG ──────────────────

print("\n═══ Test 2: Same name+company, different email – possible dup ═══")

rows_nc = [
    {
        "name": "Bob Jones",
        "email": "bob@alpha.com",
        "company": "Alpha Inc.",
        "state": "TX",
        "location": "Dallas",
        "phone": "",
        "title": "Recruiter",
        "specialization": "",
        "notes": "",
        "raw_data": "r1",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 1,
    },
    {
        "name": "  Bob  Jones ",        # normalises to same name
        "email": "robert@alpha.com",    # different email
        "company": "Alpha, Inc.",       # normalises to same company
        "state": "TX",
        "location": "Dallas",
        "phone": "555-9999",
        "title": "Senior Recruiter",
        "specialization": "Finance",
        "notes": "",
        "raw_data": "r2",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 2,
    },
]

unique2, report2 = deduplicate_and_enrich(rows_nc)

check("produces 2 unique profiles", len(unique2) == 2, f"got {len(unique2)}")
check("both flagged possible_duplicate",
      all(u.get("possible_duplicate") for u in unique2))
check("both have needs_review",
      all(u.get("needs_review") for u in unique2))
check("match_type is name_company",
      all(u.get("duplicate_match_type") == "name_company" for u in unique2))
check("report has flagged action",
      any(r["action"] == "flagged" for r in report2))


# ── Test 3: Same name only → NOT a duplicate ─────────────────────────────

print("\n═══ Test 3: Same name only – no duplicate ═══")

rows_name = [
    {
        "name": "Charlie Brown",
        "email": "charlie@one.com",
        "company": "Company A",
        "state": "CA",
        "location": "",
        "phone": "",
        "title": "",
        "specialization": "",
        "notes": "",
        "raw_data": "r1",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 1,
    },
    {
        "name": "Charlie Brown",
        "email": "charlie@two.com",
        "company": "Company B",           # different company
        "state": "NY",
        "location": "",
        "phone": "",
        "title": "",
        "specialization": "",
        "notes": "",
        "raw_data": "r2",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 2,
    },
]

unique3, report3 = deduplicate_and_enrich(rows_name)

check("produces 2 unique profiles", len(unique3) == 2, f"got {len(unique3)}")
check("neither flagged as duplicate",
      not any(u.get("possible_duplicate") for u in unique3))
check("report is empty", len(report3) == 0, f"got {len(report3)} entries")


# ── Test 4: Same company only → NOT a duplicate ──────────────────────────

print("\n═══ Test 4: Same company only – no duplicate ═══")

rows_comp = [
    {
        "name": "Dana White",
        "email": "dana@x.com",
        "company": "MegaCorp LLC",
        "state": "WA",
        "location": "",
        "phone": "",
        "title": "",
        "specialization": "",
        "notes": "",
        "raw_data": "r1",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 1,
    },
    {
        "name": "Eve Black",
        "email": "eve@x.com",
        "company": "MegaCorp LLC",
        "state": "OR",
        "location": "",
        "phone": "",
        "title": "",
        "specialization": "",
        "notes": "",
        "raw_data": "r2",
        "source_sheet": "S1",
        "source_file": "f1.xlsx",
        "row_index": 2,
    },
]

unique4, report4 = deduplicate_and_enrich(rows_comp)

check("produces 2 unique profiles", len(unique4) == 2, f"got {len(unique4)}")
check("neither flagged as duplicate",
      not any(u.get("possible_duplicate") for u in unique4))


# ── Test 5: Input rows are NOT mutated ────────────────────────────────────

print("\n═══ Test 5: Input immutability ═══")

original_row = {
    "name": "Test",
    "email": "t@t.com",
    "company": "T",
    "state": "CA",
    "location": "",
    "phone": "",
    "title": "",
    "specialization": "",
    "notes": "",
    "raw_data": "raw",
    "source_sheet": "S",
    "source_file": "f.xlsx",
    "row_index": 0,
}
import copy
snapshot = copy.deepcopy(original_row)
deduplicate_and_enrich([original_row])
check("input row not mutated", original_row == snapshot)


# ── Summary ───────────────────────────────────────────────────────────────

print(f"\n{'═' * 50}")
print(f"  Results:  {PASS} passed,  {FAIL} failed")
print(f"{'═' * 50}\n")

sys.exit(1 if FAIL else 0)
