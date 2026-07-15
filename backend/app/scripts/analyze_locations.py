import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

conn = engine.connect()

# Sample diverse location strings
print("=== SAMPLE LOCATION STRINGS (random 30) ===")
rows = conn.execute(text("""
    SELECT location FROM (
        SELECT DISTINCT location FROM recruiters 
        WHERE is_active = true AND location IS NOT NULL AND location != ''
    ) sub ORDER BY random() LIMIT 30
""")).fetchall()
for r in rows:
    print(f"  '{r[0]}'")

# Check records that HAVE location but are MISSING state
print("\n=== HAVE location, MISSING state (samples) ===")
rows2 = conn.execute(text("""
    SELECT location, state, normalized_city FROM recruiters 
    WHERE is_active = true 
      AND location IS NOT NULL AND location != ''
      AND (state IS NULL OR state = '')
    ORDER BY random() LIMIT 15
""")).fetchall()
for r in rows2:
    print(f"  loc='{r[0]}' | state='{r[1]}' | city='{r[2]}'")

# Check records that HAVE state properly filled
print("\n=== CORRECTLY FILLED state+city (samples) ===")
rows3 = conn.execute(text("""
    SELECT location, state, normalized_city FROM recruiters 
    WHERE is_active = true 
      AND state IS NOT NULL AND state != ''
      AND normalized_city IS NOT NULL AND normalized_city != ''
    ORDER BY random() LIMIT 15
""")).fetchall()
for r in rows3:
    print(f"  loc='{r[0]}' | state='{r[1]}' | city='{r[2]}'")

# Check what companies have mixed location coverage
print("\n=== COMPANY PEER LOCATION COVERAGE (top 10 with gaps) ===")
rows4 = conn.execute(text("""
    SELECT c.company_name,
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE r.location IS NOT NULL AND r.location != '') as with_loc,
        COUNT(*) FILTER (WHERE r.location IS NULL OR r.location = '') as without_loc
    FROM recruiters r
    JOIN companies c ON r.company_id = c.company_id
    WHERE r.is_active = true
    GROUP BY c.company_name
    HAVING COUNT(*) FILTER (WHERE r.location IS NULL OR r.location = '') > 0
       AND COUNT(*) FILTER (WHERE r.location IS NOT NULL AND r.location != '') > 0
    ORDER BY COUNT(*) FILTER (WHERE r.location IS NULL OR r.location = '') DESC
    LIMIT 10
""")).fetchall()
for r in rows4:
    print(f"  {r[0]:40s} total={r[1]} with_loc={r[2]} without_loc={r[3]}")

# Count location format patterns
print("\n=== LOCATION FORMAT PATTERNS ===")
patterns = conn.execute(text("""
    SELECT 
        COUNT(*) FILTER (WHERE location ~ '^[^,]+, [A-Z]{2}$') as city_state_abbrev,
        COUNT(*) FILTER (WHERE location ~ '^[^,]+, [A-Z]{2} \d{5}') as city_state_zip,
        COUNT(*) FILTER (WHERE location LIKE '%United States%' OR location LIKE '%USA%') as has_country,
        COUNT(*) FILTER (WHERE location LIKE 'Remote%') as remote,
        COUNT(*) FILTER (WHERE location LIKE 'Greater%') as greater,
        COUNT(*) FILTER (WHERE location LIKE '%Metropolitan%' OR location LIKE '%Metro%' OR location LIKE '%Area%') as metro_area,
        COUNT(*) FILTER (WHERE location ~ '^\w+$') as single_word,
        COUNT(*) FILTER (WHERE location IS NOT NULL AND location != '') as total_with_loc
    FROM recruiters WHERE is_active = true
""")).fetchone()
print(f"  'City, ST' format:          {patterns[0]}")
print(f"  'City, ST ZIP' format:      {patterns[1]}")
print(f"  Has country suffix:         {patterns[2]}")
print(f"  Remote prefix:              {patterns[3]}")
print(f"  Greater prefix:             {patterns[4]}")
print(f"  Metro/Area:                 {patterns[5]}")
print(f"  Single word:                {patterns[6]}")
print(f"  Total with location:        {patterns[7]}")

conn.close()
