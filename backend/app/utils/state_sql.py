"""Shared SQL for resolving a recruiter's effective US state."""

UNKNOWN_STATE_SENTINEL = "Unknown"

EFFECTIVE_RECRUITER_STATE_SQL = """
COALESCE(
    NULLIF(TRIM(recruiters.state), ''),
    CASE
        WHEN recruiters.location ~ '^[A-Za-z]{2}$' THEN UPPER(recruiters.location)
        WHEN recruiters.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(recruiters.location FROM '([A-Za-z]{2})$'))
        ELSE NULL
    END,
    NULLIF(TRIM(companies.state), ''),
    CASE
        WHEN companies.location ~ '^[A-Za-z]{2}$' THEN UPPER(companies.location)
        WHEN companies.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(companies.location FROM '([A-Za-z]{2})$'))
        ELSE NULL
    END
)
"""

EFFECTIVE_RECRUITER_STATE_SQL_R = """
COALESCE(
    NULLIF(TRIM(r.state), ''),
    CASE
        WHEN r.location ~ '^[A-Za-z]{2}$' THEN UPPER(r.location)
        WHEN r.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(r.location FROM '([A-Za-z]{2})$'))
        ELSE NULL
    END,
    NULLIF(TRIM(c.state), ''),
    CASE
        WHEN c.location ~ '^[A-Za-z]{2}$' THEN UPPER(c.location)
        WHEN c.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(c.location FROM '([A-Za-z]{2})$'))
        ELSE NULL
    END
)
"""
