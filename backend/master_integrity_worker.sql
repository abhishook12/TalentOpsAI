CREATE OR REPLACE FUNCTION talentops_maintenance.check_recruiters()
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $$
DECLARE
    profile record;
    meta jsonb;
    claim jsonb;
    quarantine jsonb;
    checked integer := 0;
    archive_claim boolean;
    inferred_stamp boolean;
    work_mode_location boolean;
    page_label_company boolean;
BEGIN
    FOR profile IN
        SELECT r.recruiter_id, r.metadata_json, r.email_status, r.email_verified_at,
               r.location, r.company_id, c.company_name
        FROM public.recruiters r
        LEFT JOIN public.companies c ON c.company_id = r.company_id
        WHERE r.integrity_checked_at IS NULL OR r.integrity_checked_at < now() - interval '7 days'
        ORDER BY (r.location ~* '^(remote|hybrid|on[- ]?site|work from home)$' OR c.company_name ~* '^(our team|meet (our|the) team|careers|jobs|about us)([[:space:]]*[-–—:|]|$)') DESC, r.integrity_checked_at ASC NULLS FIRST, r.recruiter_id
        LIMIT 200 FOR UPDATE OF r SKIP LOCKED
    LOOP
        meta := COALESCE(CASE WHEN pg_input_is_valid(profile.metadata_json, 'jsonb')
                              THEN profile.metadata_json::jsonb END, '{}'::jsonb);
        claim := meta -> 'nsr_profile';
        archive_claim := claim ->> 'registry' = 'NASSCOM National Skills Registry (NSR)'
            AND claim ->> 'itpin' ~ '^[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{2}$'
            AND claim ->> 'notes' IN ('Standard NSR registry profile',
                'Verified candidate dossier pre-cleared for enterprise client deployment')
            AND (NOT meta ? 'quarantined_synthetic_nsr_profile'
                 OR meta -> 'quarantined_synthetic_nsr_profile' = claim);
        inferred_stamp := profile.email_verified_at IS NOT NULL AND upper(profile.email_status)
            IN ('PATTERN_VERIFIED','MX_VERIFIED','SYNTHESIZED_MX_VERIFIED','CATCHALL_VERIFIED','PATTERN_PREDICTED');
        work_mode_location := profile.location ~* '^(remote|hybrid|on[- ]?site|work from home)$';
        page_label_company := profile.company_name ~* '^(our team|meet (our|the) team|careers|jobs|about us)([[:space:]]*[-–—:|]|$)';
        quarantine := COALESCE(meta -> 'integrity_quarantine', '{}'::jsonb)
            || CASE WHEN work_mode_location THEN jsonb_build_object('location', jsonb_build_object('value', profile.location, 'reason', 'work_mode_is_not_location', 'archived_at', now())) ELSE '{}'::jsonb END
            || CASE WHEN page_label_company THEN jsonb_build_object('employer', jsonb_build_object('company_id', profile.company_id, 'value', profile.company_name, 'reason', 'page_label_is_not_employer', 'archived_at', now())) ELSE '{}'::jsonb END;
        IF inferred_stamp THEN
            INSERT INTO talentops_maintenance.email_evidence_history
                (recruiter_id, previous_status, previous_verified_at)
            VALUES (profile.recruiter_id, profile.email_status, profile.email_verified_at)
            ON CONFLICT DO NOTHING;
        END IF;
        UPDATE public.recruiters SET
            metadata_json = (
                CASE WHEN archive_claim THEN
                    (meta - 'nsr_profile') || jsonb_build_object('quarantined_synthetic_nsr_profile', claim)
                ELSE meta END
                || CASE WHEN work_mode_location OR page_label_company
                        THEN jsonb_build_object('integrity_quarantine', quarantine)
                        ELSE '{}'::jsonb END
            )::text,
            email_verified_at = CASE WHEN inferred_stamp THEN NULL ELSE email_verified_at END,
            location = CASE WHEN work_mode_location THEN NULL ELSE location END,
            company_id = CASE WHEN page_label_company THEN NULL ELSE company_id END,
            needs_review = CASE WHEN page_label_company THEN true ELSE needs_review END,
            review_reason = CASE WHEN page_label_company THEN 'Employer value came from a page label and needs new evidence' ELSE review_reason END,
            integrity_checked_at = now(), last_scan_at = timezone('UTC', now())
        WHERE recruiter_id = profile.recruiter_id;
        checked := checked + 1;
    END LOOP;
    RETURN checked;
END;
$$;