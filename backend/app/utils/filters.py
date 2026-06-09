from sqlalchemy import or_, and_, String, cast
from sqlalchemy.orm import joinedload, contains_eager
from app.models.models import Recruiter, Company
from app.utils.normalizer import normalize_text

def apply_state_filter(query, state: str):
    """
    Consistently filters recruiters by state.
    Matches if the recruiter is explicitly in the state,
    OR if the recruiter's state is blank/missing AND their company is in the state.
    """
    return query.filter(
        or_(
            Recruiter.state == state,
            and_(
                or_(Recruiter.state == None, Recruiter.state == ''),
                Company.state == state
            )
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
