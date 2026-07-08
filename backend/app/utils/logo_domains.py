from .normalizer import extract_domain

THIRD_PARTY_LOGO_DOMAINS = {
    "apollo.io",
    "crunchbase.com",
    "facebook.com",
    "glassdoor.com",
    "hasdic.org",
    "indeed.com",
    "linkedin.com",
    "rocketreach.co",
    "signalhire.com",
    "twitter.com",
    "wikipedia.org",
    "x.com",
    "zoominfo.com",
}


def is_usable_logo_domain(value: str | None) -> bool:
    domain = extract_domain(value or "")
    return bool(domain) and domain not in THIRD_PARTY_LOGO_DOMAINS


def select_logo_domain(website: str | None, email_pattern: str | None) -> str | None:
    for value in (website, email_pattern):
        if is_usable_logo_domain(value):
            return extract_domain(value or "")
    return None
