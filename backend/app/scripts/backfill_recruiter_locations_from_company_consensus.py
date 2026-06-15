from __future__ import annotations

from sqlalchemy import text

from app.database import SessionLocal


CONSENSUS_SQL = text(
    r"""
WITH clean_recruiter_locations AS (
    SELECT
        company_id,
        BTRIM(location) AS location,
        COUNT(*) AS cnt
    FROM recruiters
    WHERE company_id IS NOT NULL
      AND location IS NOT NULL
      AND BTRIM(location) <> ''
      AND location ~ '[A-Za-z]'
      AND location !~ '@|www\.|http|#ERROR!|^NIL$|^nil$|^N/A$|^NA$|^-$'
      AND location !~ '(^|[^A-Za-z])[0-9]{3}[-\.\s]?[0-9]{3}[-\.\s]?[0-9]{4}([^0-9]|$)'
    GROUP BY company_id, BTRIM(location)
),
ranked AS (
    SELECT
        company_id,
        location,
        cnt,
        SUM(cnt) OVER (PARTITION BY company_id) AS total_cnt,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY cnt DESC, location) AS rn
    FROM clean_recruiter_locations
),
safe_company_location AS (
    SELECT company_id, location
    FROM ranked
    WHERE rn = 1
      AND cnt >= 2
      AND cnt * 1.0 / NULLIF(total_cnt, 0) >= 0.75
      AND location ~ ','
)
UPDATE recruiters AS r
SET
    location = s.location,
    state = CASE
        WHEN s.location ~ ',\s*([A-Z]{2})($|[^A-Za-z])'
            THEN UPPER(SUBSTRING(s.location FROM ',\s*([A-Z]{2})($|[^A-Za-z])'))
        ELSE state
    END,
    location_confidence = 'medium',
    state_source = CASE
        WHEN r.state IS NULL OR BTRIM(r.state) = ''
            THEN 'company_location_consensus'
        ELSE r.state_source
    END,
    state_reason = CASE
        WHEN r.state IS NULL OR BTRIM(r.state) = ''
            THEN 'Filled from high-consensus company recruiter location'
        ELSE r.state_reason
    END
FROM safe_company_location AS s
WHERE r.company_id = s.company_id
  AND (r.location IS NULL OR BTRIM(r.location) = '')
RETURNING r.recruiter_id, r.recruiter_name, r.company_id, r.location, r.state
"""
)


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(CONSENSUS_SQL).mappings().all()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"updated_recruiters={len(rows)}")
    for row in rows:
        print(
            f"{row['recruiter_id']} | {row['recruiter_name']} | "
            f"company_id={row['company_id']} | location={row['location']} | state={row['state']}"
        )


if __name__ == "__main__":
    main()
