-- ============================================================
-- TalentOps AI — Email-based Deduplication Merge
-- Strategy: where email2 of record A = primary email of record B
--   → merge phone numbers into the KEPT record
--   → delete the duplicate record
-- ============================================================

BEGIN;

-- Step 1: Create a temp table of merge pairs
-- keep_id = record we keep, del_id = record we delete
CREATE TEMP TABLE merge_pairs AS
WITH pairs AS (
    SELECT
        r1.recruiter_id  AS id1,
        r1.recruiter_name AS name1,
        r1.email         AS email1,
        r1.email2        AS email2_1,
        r1.phone         AS phone1,
        r1.phone2        AS phone2_1,
        r1.linkedin      AS linkedin1,
        r1.specialization AS spec1,
        r1.notes         AS notes1,
        r1.company_id    AS cid1,
        r2.recruiter_id  AS id2,
        r2.recruiter_name AS name2,
        r2.email         AS email2,
        r2.email2        AS email2_2,
        r2.phone         AS phone2,
        r2.phone2        AS phone2_2,
        r2.linkedin      AS linkedin2,
        r2.specialization AS spec2,
        r2.notes         AS notes2,
        r2.company_id    AS cid2
    FROM recruiters r1
    JOIN recruiters r2
        ON LOWER(TRIM(r1.email2)) = LOWER(TRIM(r2.email))
        AND r1.recruiter_id != r2.recruiter_id
    WHERE r1.email2 IS NOT NULL AND TRIM(r1.email2) != ''
),
-- Decide which to keep: prefer the one with the longer/proper name,
-- or the lower ID (first imported) as tiebreaker
scored AS (
    SELECT *,
        -- Score name quality: count of words + penalize if name = email-prefix style (no space)
        (   CASE WHEN name1 ~ ' ' THEN 2 ELSE 0 END
          + CASE WHEN name1 = initcap(name1) THEN 1 ELSE 0 END
          + LENGTH(name1)
        ) AS score1,
        (   CASE WHEN name2 ~ ' ' THEN 2 ELSE 0 END
          + CASE WHEN name2 = initcap(name2) THEN 1 ELSE 0 END
          + LENGTH(name2)
        ) AS score2
    FROM pairs
)
SELECT
    CASE WHEN score1 >= score2 THEN id1  ELSE id2  END AS keep_id,
    CASE WHEN score1 >= score2 THEN id2  ELSE id1  END AS del_id,
    CASE WHEN score1 >= score2 THEN name1 ELSE name2 END AS keep_name,
    CASE WHEN score1 >= score2 THEN email1 ELSE email2 END AS keep_email,
    CASE WHEN score1 >= score2 THEN email2 ELSE email1 END AS keep_email2,
    -- Merge phones: pick first non-null unique phone for phone slot
    CASE
        WHEN score1 >= score2 THEN
            COALESCE(NULLIF(TRIM(phone1),''),  NULLIF(TRIM(phone2),''),  NULLIF(TRIM(phone2_1),''), NULLIF(TRIM(phone2_2),''))
        ELSE
            COALESCE(NULLIF(TRIM(phone2),''),  NULLIF(TRIM(phone1),''),  NULLIF(TRIM(phone2_2),''), NULLIF(TRIM(phone2_1),''))
    END AS merged_phone,
    -- For phone2: pick a DIFFERENT number than phone
    CASE
        WHEN score1 >= score2 THEN
            CASE
                WHEN NULLIF(TRIM(phone2_1),'') IS NOT NULL
                     AND REGEXP_REPLACE(COALESCE(phone2_1,''), '[^0-9]','','g') !=
                         REGEXP_REPLACE(COALESCE(phone1,''), '[^0-9]','','g')
                THEN NULLIF(TRIM(phone2_1),'')
                WHEN NULLIF(TRIM(phone2),'') IS NOT NULL
                     AND REGEXP_REPLACE(COALESCE(phone2,''), '[^0-9]','','g') !=
                         REGEXP_REPLACE(COALESCE(phone1,''), '[^0-9]','','g')
                THEN NULLIF(TRIM(phone2),'')
                ELSE NULLIF(TRIM(phone2_2),'')
            END
        ELSE
            CASE
                WHEN NULLIF(TRIM(phone2_2),'') IS NOT NULL
                     AND REGEXP_REPLACE(COALESCE(phone2_2,''), '[^0-9]','','g') !=
                         REGEXP_REPLACE(COALESCE(phone2,''), '[^0-9]','','g')
                THEN NULLIF(TRIM(phone2_2),'')
                WHEN NULLIF(TRIM(phone1),'') IS NOT NULL
                     AND REGEXP_REPLACE(COALESCE(phone1,''), '[^0-9]','','g') !=
                         REGEXP_REPLACE(COALESCE(phone2,''), '[^0-9]','','g')
                THEN NULLIF(TRIM(phone1),'')
                ELSE NULLIF(TRIM(phone2_1),'')
            END
    END AS merged_phone2,
    CASE WHEN score1 >= score2 THEN COALESCE(linkedin1, linkedin2) ELSE COALESCE(linkedin2, linkedin1) END AS merged_linkedin,
    CASE WHEN score1 >= score2 THEN COALESCE(spec1, spec2) ELSE COALESCE(spec2, spec1) END AS merged_spec,
    CASE WHEN score1 >= score2 THEN COALESCE(cid1, cid2) ELSE COALESCE(cid2, cid1) END AS merged_company
FROM scored;

-- Preview what will be merged
SELECT
    keep_id, del_id, keep_name, keep_email, keep_email2,
    merged_phone AS phone, merged_phone2 AS phone2
FROM merge_pairs
ORDER BY keep_id;

-- Step 2: Update kept records with merged data
UPDATE recruiters r
SET
    recruiter_name  = mp.keep_name,
    email           = mp.keep_email,
    email2          = mp.keep_email2,
    phone           = mp.merged_phone,
    phone2          = mp.merged_phone2,
    linkedin        = COALESCE(mp.merged_linkedin, r.linkedin),
    specialization  = COALESCE(mp.merged_spec, r.specialization),
    company_id      = COALESCE(mp.merged_company, r.company_id)
FROM merge_pairs mp
WHERE r.recruiter_id = mp.keep_id;

-- Step 3: Delete duplicate records
DELETE FROM recruiters
WHERE recruiter_id IN (SELECT del_id FROM merge_pairs);

-- Final count
SELECT COUNT(*) AS total_after FROM recruiters;

COMMIT;
