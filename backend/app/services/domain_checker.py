import time
import logging
import dns.resolver
from functools import lru_cache
from dataclasses import dataclass
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

@dataclass
class DomainCheckResult:
    exists: bool
    has_mx: bool
    mx_records: list[str]
    is_parked: bool
    is_disposable: bool
    is_free_provider: bool
    accepts_mail: bool
    check_time_ms: float

class DomainChecker:
    DISPOSABLE_DOMAINS = {
        "mailinator.com", "guerrillamail.com", "yopmail.com", "10minutemail.com", 
        "tempmail.com", "throwaway.email", "temp-mail.org", "sharklasers.com",
        "spam4.me", "fakemail.net", "dispostable.com", "trashmail.com",
        "tempmailaddress.com", "getairmail.com", "emailondeck.com", "tempmail.net",
        "mintemail.com", "maildrop.cc", "tempmail.co.com", "mytrashmail.com",
        "spamgourmet.com", "jetable.org", "incognitomail.com", "anonbox.net",
        "spambog.com", "0clickemail.com", "tempail.com", "mailexpire.com",
        "pookmail.com", "fakeinbox.com", "gator.com", "spamex.com", "binkmail.com",
        "spamhole.com", "dodgeit.com", "e4ward.com", "gishpuppy.com", "spammotel.com",
        "safetymail.info", "mailforspam.com", "bouncr.com", "spambox.us",
        "sneakemail.com", "zoemail.com", "despammed.com", "mailnull.com",
        "spam.la", "trbvm.com", "mailcatch.com", "temp-mail.cc", "mailnesia.com"
    }

    FREE_PROVIDERS = {
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", 
        "icloud.com", "protonmail.com", "live.com", "msn.com", "yandex.com",
        "gmx.com", "zoho.com", "mail.com", "yahoo.co.uk", "hotmail.co.uk",
        "mac.com", "me.com", "googlemail.com"
    }

    PARKING_SERVICES = {
        "sedoparking.com", "parkingcrew.net", "bodis.com", "above.com",
        "parked.com", "domainname.com", "dsredir.com"
    }

    ROLE_ACCOUNTS = {
        "info", "admin", "sales", "support", "contact", "hr", "jobs", 
        "careers", "noreply", "no-reply", "billing", "marketing", "team", 
        "hello", "webmaster", "postmaster", "hostmaster", "abuse"
    }

    def __init__(self):
        # Create a custom resolver with a 5-second timeout
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5
        self.resolver.lifetime = 5

    @lru_cache(maxsize=10000)
    def check_domain(self, domain: str) -> DomainCheckResult:
        """
        Check email domain for existence, MX records, and reputation.
        """
        start_time = time.time()
        domain = domain.lower().strip()
        
        exists = False
        has_mx = False
        mx_records = []
        is_parked = False
        is_disposable = domain in self.DISPOSABLE_DOMAINS
        is_free_provider = domain in self.FREE_PROVIDERS
        accepts_mail = False

        try:
            # Query for MX records
            answers = self.resolver.resolve(domain, 'MX')
            exists = True
            if answers:
                has_mx = True
                for rdata in answers:
                    exchange = str(rdata.exchange).rstrip('.').lower()
                    mx_records.append(exchange)
                    
                    # Check for parked domains
                    if any(parking in exchange for parking in self.PARKING_SERVICES):
                        is_parked = True
                
                if has_mx and not is_parked:
                    accepts_mail = True

        except dns.resolver.NXDOMAIN:
            # Domain does not exist
            exists = False
        except dns.resolver.NoAnswer:
            # Domain exists but has no MX records
            exists = True
            # We can also check if A record exists for accepts_mail fallback,
            # but usually we strictly require MX for email validation.
        except dns.resolver.Timeout:
            logger.warning(f"DNS timeout while resolving MX for {domain}")
        except Exception as e:
            logger.warning(f"Error resolving MX for {domain}: {str(e)}")

        # Calculate time taken
        check_time_ms = (time.time() - start_time) * 1000

        return DomainCheckResult(
            exists=exists,
            has_mx=has_mx,
            mx_records=mx_records,
            is_parked=is_parked,
            is_disposable=is_disposable,
            is_free_provider=is_free_provider,
            accepts_mail=accepts_mail,
            check_time_ms=check_time_ms
        )

    def is_role_account(self, local_part: str) -> bool:
        """
        Check if the local part of an email is a role account.
        """
        return local_part.lower().strip() in self.ROLE_ACCOUNTS

    def validate_syntax(self, email: str) -> tuple[bool, str]:
        """
        Validate email syntax using email_validator.
        Returns (is_valid, error_message)
        """
        try:
            validate_email(email, check_deliverability=False)
            return True, ""
        except EmailNotValidError as e:
            return False, str(e)

domain_checker = DomainChecker()
