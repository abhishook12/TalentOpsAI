"""Shared SQL for resolving a recruiter's effective US state."""

import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or ""
IS_SQLITE = not db_url.startswith("postgresql")

UNKNOWN_STATE_SENTINEL = "Unknown"

if IS_SQLITE:
    EFFECTIVE_RECRUITER_STATE_SQL = """
    COALESCE(
        NULLIF(TRIM(recruiters.state), ''),
        NULLIF(TRIM(companies.state), '')
    )
    """
    EFFECTIVE_RECRUITER_STATE_SQL_R = """
    COALESCE(
        NULLIF(TRIM(r.state), ''),
        NULLIF(TRIM(c.state), '')
    )
    """
else:
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
