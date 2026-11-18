-- Run once per database. The scheduler survives app restarts and PC shutdowns.
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE SCHEMA IF NOT EXISTS talentops_maintenance;
REVOKE ALL ON SCHEMA talentops_maintenance FROM PUBLIC, anon, authenticated;

ALTER TABLE public.recruiters ADD COLUMN IF NOT EXISTS integrity_checked_at timestamptz;
CREATE INDEX IF NOT EXISTS recruiters_integrity_due_idx
    ON public.recruiters (integrity_checked_at ASC NULLS FIRST, recruiter_id);

CREATE TABLE IF NOT EXISTS talentops_maintenance.email_evidence_history (
    recruiter_id bigint NOT NULL,
    previous_status text NOT NULL,
    previous_verified_at timestamp NOT NULL,
    archived_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (recruiter_id, previous_status, previous_verified_at)
);

CREATE OR REPLACE FUNCTION talentops_maintenance.check_recruiters()
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $$
DECLARE
    profile record;
    meta jsonb;
    claim jsonb;
    checked integer := 0;
    archive_claim boolean;
    inferred_stamp boolean;
BEGIN
    FOR profile IN
        SELECT recruiter_id, metadata_json, email_status, email_verified_at
        FROM public.recruiters
        WHERE integrity_checked_at IS NULL OR integrity_checked_at < now() - interval '7 days'
        ORDER BY integrity_checked_at ASC NULLS FIRST, recruiter_id
        LIMIT 200 FOR UPDATE SKIP LOCKED
    LOOP
        meta := CASE WHEN pg_input_is_valid(profile.metadata_json, 'jsonb')
                     THEN profile.metadata_json::jsonb END;
        claim := meta -> 'nsr_profile';
        archive_claim := claim ->> 'registry' = 'NASSCOM National Skills Registry (NSR)'
            AND claim ->> 'itpin' ~ '^[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{2}$'
            AND claim ->> 'notes' IN ('Standard NSR registry profile',
                'Verified candidate dossier pre-cleared for enterprise client deployment')
            AND (NOT meta ? 'quarantined_synthetic_nsr_profile'
                 OR meta -> 'quarantined_synthetic_nsr_profile' = claim);
        inferred_stamp := profile.email_verified_at IS NOT NULL AND upper(profile.email_status)
            IN ('PATTERN_VERIFIED','MX_VERIFIED','SYNTHESIZED_MX_VERIFIED','CATCHALL_VERIFIED','PATTERN_PREDICTED');
        IF inferred_stamp THEN
            INSERT INTO talentops_maintenance.email_evidence_history
                (recruiter_id, previous_status, previous_verified_at)
            VALUES (profile.recruiter_id, profile.email_status, profile.email_verified_at)
            ON CONFLICT DO NOTHING;
        END IF;
        UPDATE public.recruiters SET
            metadata_json = CASE WHEN archive_claim THEN
                ((meta - 'nsr_profile') || jsonb_build_object('quarantined_synthetic_nsr_profile', claim))::text
                ELSE metadata_json END,
            email_verified_at = CASE WHEN inferred_stamp THEN NULL ELSE email_verified_at END,
            integrity_checked_at = now(), last_scan_at = timezone('UTC', now())
        WHERE recruiter_id = profile.recruiter_id;
        checked := checked + 1;
    END LOOP;
    RETURN checked;
END;
$$;
REVOKE ALL ON FUNCTION talentops_maintenance.check_recruiters() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE talentops_maintenance.email_evidence_history FROM PUBLIC, anon, authenticated;
SELECT cron.schedule('talentops-master-integrity', '* * * * *',
                     'SELECT talentops_maintenance.check_recruiters()');
