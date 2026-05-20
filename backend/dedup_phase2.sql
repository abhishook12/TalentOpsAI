-- ============================================================
-- TalentOps AI — Phase 2 Deep Dedup: Same Name + Same Domain
-- Merges recruiters with same full name at same email domain
-- (e.g. dan.hoglund@ + dan@ at same company = same person)
-- SKIPS generic/shared accounts like recruit*, rec*, hr*, info*
-- ============================================================

BEGIN;

CREATE TEMP TABLE phase2_pairs AS
WITH dup_groups AS (
    SELECT
        LOWER(TRIM(recruiter_name))         AS norm_name,
        SPLIT_PART(LOWER(TRIM(email)),'@',2) AS domain,
        COUNT(*)                             AS cnt,
        MIN(recruiter_id)                    AS keep_id,
        ARRAY_AGG(recruiter_id ORDER BY recruiter_id) AS all_ids
    FROM recruiters
    WHERE
        recruiter_name IS NOT NULL
        -- Must have at least first + last name (space in name) OR known short alias
        AND (recruiter_name ~ ' ' OR LENGTH(TRIM(recruiter_name)) > 5)
        -- Skip obviously generic/shared accounts
        AND LOWER(TRIM(recruiter_name)) NOT IN (
            'recruit','recruiter','rec','hr','info','admin','staff','team',
            'recruiting','staffing','talent','unknown','user','test'
        )
        AND LOWER(TRIM(recruiter_name)) NOT LIKE 'recruit%'
        AND LOWER(TRIM(recruiter_name)) NOT LIKE 'rec%'
        AND email IS NOT NULL
    GROUP BY norm_name, domain
    HAVING COUNT(*) > 1
),
-- Explode: for each group, pair every non-min ID with the keep_id
pairs AS (
    SELECT
        g.keep_id,
        UNNEST(ARRAY_REMOVE(g.all_ids, g.keep_id)) AS del_id
    FROM dup_groups g
)
SELECT
    p.keep_id,
    p.del_id,
    r_keep.recruiter_name AS keep_name,
    r_keep.email          AS keep_email,
    r_del.email           AS del_email,
    -- Merge phones: keep has priority, fill from del if missing
    COALESCE(NULLIF(TRIM(r_keep.phone),''),  NULLIF(TRIM(r_del.phone),''))  AS merged_phone,
    CASE
        WHEN NULLIF(TRIM(r_keep.phone2),'') IS NOT NULL THEN NULLIF(TRIM(r_keep.phone2),'')
        WHEN NULLIF(TRIM(r_del.phone2),'') IS NOT NULL  THEN NULLIF(TRIM(r_del.phone2),'')
        -- If del's phone is different from keep's phone, put it in phone2
        WHEN NULLIF(TRIM(r_del.phone),'') IS NOT NULL
             AND REGEXP_REPLACE(COALESCE(r_del.phone,''),'[^0-9]','','g')
              != REGEXP_REPLACE(COALESCE(r_keep.phone,''),'[^0-9]','','g')
        THEN NULLIF(TRIM(r_del.phone),'')
        ELSE NULL
    END AS merged_phone2,
    COALESCE(NULLIF(TRIM(r_keep.email2),''), NULLIF(TRIM(r_del.email2),''), NULLIF(TRIM(r_del.email),'')) AS merged_email2,
    COALESCE(r_keep.linkedin, r_del.linkedin)           AS merged_linkedin,
    COALESCE(r_keep.specialization, r_del.specialization) AS merged_spec,
    COALESCE(r_keep.notes, r_del.notes)                 AS merged_notes,
    COALESCE(r_keep.company_id, r_del.company_id)       AS merged_company
FROM pairs p
JOIN recruiters r_keep ON r_keep.recruiter_id = p.keep_id
JOIN recruiters r_del  ON r_del.recruiter_id  = p.del_id;

-- Preview
SELECT keep_id, del_id, keep_name, keep_email, del_email,
       merged_phone AS phone, merged_phone2 AS phone2
FROM phase2_pairs
ORDER BY keep_name;

-- Apply updates to kept records
UPDATE recruiters r
SET
    phone          = mp.merged_phone,
    phone2         = mp.merged_phone2,
    email2         = mp.merged_email2,
    linkedin       = COALESCE(mp.merged_linkedin,   r.linkedin),
    specialization = COALESCE(mp.merged_spec,       r.specialization),
    notes          = COALESCE(mp.merged_notes,       r.notes),
    company_id     = COALESCE(mp.merged_company,     r.company_id)
FROM phase2_pairs mp
WHERE r.recruiter_id = mp.keep_id;

-- Delete duplicates
DELETE FROM recruiters
WHERE recruiter_id IN (SELECT del_id FROM phase2_pairs);

-- Final summary
SELECT
    (SELECT COUNT(*) FROM phase2_pairs) AS pairs_merged,
    (SELECT COUNT(*) FROM recruiters)   AS total_after;

COMMIT;
