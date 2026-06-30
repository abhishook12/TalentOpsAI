from sqlalchemy import text
from sqlalchemy.orm import joinedload, contains_eager
from ..models.models import Recruiter, Company
from .normalizer import normalize_text
from .state_sql import EFFECTIVE_RECRUITER_STATE_SQL, UNKNOWN_STATE_SENTINEL

def apply_state_filter(query, state: str):
    """
    Filter recruiters by effective state — same resolution used in analytics
    and the Directory state picker (explicit state, parsed location, company state).
    """
    state_value = (state or '').strip()
    if not state_value:
        return query

    if state_value.upper() == UNKNOWN_STATE_SENTINEL.upper():
        return query.filter(text(f"({EFFECTIVE_RECRUITER_STATE_SQL}) IS NULL"))

    return query.filter(
        text(f"({EFFECTIVE_RECRUITER_STATE_SQL}) = :effective_state").bindparams(
            effective_state=state_value.upper()
        )
    )

def apply_company_filter(query, company_search_term: str):
    """
    Consistently filters recruiters by company name using the normalized_company_name column.
    """
    clean_company = normalize_text(company_search_term)
    return query.filter(
        Company.normalized_company_name.ilike(f"%{clean_company}%")
    )
