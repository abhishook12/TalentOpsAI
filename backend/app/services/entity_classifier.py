"""
EntityTypeClassifier — Hard Entity Type Classification Engine.

Classifies every DiscoveryStaging record into exactly ONE entity type
BEFORE any processing happens. This is the FIRST gate in the pipeline.

Entity Types:
  PERSON        — Individual human being (recruiter, candidate, contact)
  COMPANY       — Business organization, staffing agency, corporation
  JOB_POSTING   — Job listing, vacancy, hiring requirement
  CONTACT_INFO  — Generic contact page data (email/phone without person)
  MARKET_SIGNAL — Industry trend, hiring signal, market intelligence
  NOISE         — UI artifacts, platform chrome, navigation elements

The classifier returns a hard verdict with confidence. Records are then
routed to completely separate processing paths based on their type.
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger('talentops.entity_classifier')

# ── Entity Type Constants ─────────────────────────────────────────────
ENTITY_PERSON = 'PERSON'
ENTITY_COMPANY = 'COMPANY'
ENTITY_JOB_POSTING = 'JOB_POSTING'
ENTITY_CONTACT_INFO = 'CONTACT_INFO'
ENTITY_MARKET_SIGNAL = 'MARKET_SIGNAL'
ENTITY_NOISE = 'NOISE'

ALL_ENTITY_TYPES = frozenset({
    ENTITY_PERSON, ENTITY_COMPANY, ENTITY_JOB_POSTING,
    ENTITY_CONTACT_INFO, ENTITY_MARKET_SIGNAL, ENTITY_NOISE,
})


class EntityTypeClassifier:
    """
    Deterministic Entity Type Classifier.
    
    Uses a cascading rule engine (no ML) to classify entities:
    1. NOISE detection first (cheapest, highest precision)
    2. COMPANY detection (structural signals: legal suffixes, domain terms)
    3. JOB_POSTING detection (job title patterns, posting indicators)
    4. CONTACT_INFO detection (generic email/phone without person identity)
    5. MARKET_SIGNAL detection (hiring signals, industry trends)
    6. Default: PERSON (most staging records are people)
    """
    
    def classify(self,
                 raw_name: Optional[str],
                 raw_title: Optional[str] = None,
                 raw_company: Optional[str] = None,
                 raw_email: Optional[str] = None,
                 raw_phone: Optional[str] = None,
                 source_url: Optional[str] = None,
                 source_page_title: Optional[str] = None,
                 extraction_source: Optional[str] = None,
                 ) -> Dict[str, Any]:
        """
        Classify a staging record into an entity type.
        
        Returns:
            {
                'entity_type': str,       # One of ALL_ENTITY_TYPES
                'confidence': float,      # 0.0 - 1.0
                'reason': str,            # Human-readable classification reason
                'signals': list[str],     # List of signals that contributed
            }
        """
        signals = []
        name = (raw_name or '').strip()
        # Clean relative timestamp noise e.g. "Fineta Consulting · 20 minutes ago"
        name = re.sub(r"\s*[·•|]\s*\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|secs?|mins?|hrs?|d|w|m|h|y)\s*ago.*$", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s*[·•|]\s*(?:reposted|shared|liked|commented).*$", "", name, flags=re.IGNORECASE).strip()
        # Clean page header prefixes e.g. "About A3 Staffing Solutions" -> "A3 Staffing Solutions"
        name = re.sub(r"^(?:about|overview of|welcome to)\s+", "", name, flags=re.IGNORECASE).strip()

        title = (raw_title or '').strip()
        company = (raw_company or '').strip()
        email = (raw_email or '').strip().lower()
        url = (source_url or '').strip().lower()
        page_title = (source_page_title or '').strip().lower()
        
        name_lower = name.lower()
        title_lower = title.lower()
        
        # ── GATE 1: NOISE Detection ──────────────────────────────────
        noise_result = self._check_noise(name, name_lower, title_lower, url, page_title, signals)
        if noise_result:
            return noise_result
        
        # ── GATE 2: JOB_POSTING Detection (Prioritized so Job Titles are not classified as Companies) ──
        job_result = self._check_job_posting(name, name_lower, title, title_lower, url, page_title, signals)
        if job_result:
            return job_result
        
        # ── GATE 3: CONTACT_INFO Detection (Prioritized so Generic Desks are classified as Contacts) ────
        contact_result = self._check_contact_info(name, name_lower, title_lower, email, raw_phone, url, signals)
        if contact_result:
            return contact_result
        
        # ── GATE 4: COMPANY Detection ────────────────────────────────
        company_result = self._check_company(name, name_lower, title, title_lower, company, email, url, page_title, signals)
        if company_result:
            return company_result
        
        # ── GATE 5: MARKET_SIGNAL Detection ──────────────────────────
        signal_result = self._check_market_signal(name, name_lower, title, title_lower, url, page_title, signals)
        if signal_result:
            return signal_result
        
        # ── DEFAULT: PERSON ──────────────────────────────────────────
        # Import validate_human_name to double-check
        from ..utils.normalizer import validate_human_name
        is_valid, clean_name, reject_reason = validate_human_name(name)
        
        if is_valid:
            signals.append('valid_human_name')
            return {
                'entity_type': ENTITY_PERSON,
                'confidence': 0.85,
                'reason': f'Valid human name: {clean_name}',
                'signals': signals,
                'clean_name': clean_name,
            }
        
        # ── CamelCase & Mashed Username Recovery ─────────────────────
        # LinkedIn feed names often appear as "LucasSilverott", "Lucasleverett", "Jeffkobza"
        if len(name.split()) == 1 and len(name) >= 5:
            # Step 1: Try CamelCase split
            camel_parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            if len(camel_parts.split()) >= 2:
                is_valid_cc, clean_cc, _ = validate_human_name(camel_parts)
                if is_valid_cc:
                    signals.append('camelcase_name_recovered')
                    return {
                        'entity_type': ENTITY_PERSON,
                        'confidence': 0.80,
                        'reason': f'CamelCase username recovered: {clean_cc}',
                        'signals': signals,
                        'clean_name': clean_cc,
                    }
            
            # Step 2: Try common given name split for mashed handles e.g. "Lucasleverett" -> "Lucas Leverett"
            COMMON_GIVEN_NAMES = {
                'adam', 'alex', 'andrew', 'anthony', 'ben', 'brian', 'chris', 'dan', 'daniel',
                'david', 'eric', 'gary', 'greg', 'james', 'jason', 'jeff', 'joe', 'john',
                'justin', 'kevin', 'lucas', 'mark', 'matt', 'matthew', 'michael', 'nick',
                'paul', 'peter', 'richard', 'rob', 'robert', 'ryan', 'sam', 'sarah', 'scott',
                'steve', 'steven', 'tim', 'tom', 'thomas', 'will', 'william'
            }
            n_low = name.lower()
            for gn in sorted(COMMON_GIVEN_NAMES, key=len, reverse=True):
                if n_low.startswith(gn) and len(n_low) >= len(gn) + 3:
                    candidate_split = f"{name[:len(gn)].capitalize()} {name[len(gn):].capitalize()}"
                    is_valid_m, clean_m, _ = validate_human_name(candidate_split)
                    if is_valid_m:
                        signals.append('mashed_handle_recovered')
                        return {
                            'entity_type': ENTITY_PERSON,
                            'confidence': 0.75,
                            'reason': f'Mashed handle recovered: {clean_m}',
                            'signals': signals,
                            'clean_name': clean_m,
                        }
        
        # Name failed human validation but didn't match any other type
        # Re-check if it's actually a company that wasn't caught
        from ..utils.normalizer import is_company_name
        if is_company_name(name):
            signals.append('fallback_company_name_detected')
            return {
                'entity_type': ENTITY_COMPANY,
                'confidence': 0.80,
                'reason': f'Fallback company detection: {name}',
                'signals': signals,
            }
        
        # Truly unclassifiable — route to NOISE
        signals.append('unclassifiable_name')
        return {
            'entity_type': ENTITY_NOISE,
            'confidence': 0.60,
            'reason': f'Name failed all classification gates: {reject_reason}',
            'signals': signals,
        }
    
    def _check_noise(self, name, name_lower, title_lower, url, page_title, signals) -> Optional[Dict]:
        """Detect UI artifacts, platform chrome, navigation noise."""
        from ..utils.normalizer import is_ui_action, is_platform_name
        
        if not name or len(name.strip()) < 2:
            signals.append('empty_name')
            return {
                'entity_type': ENTITY_NOISE,
                'confidence': 1.0,
                'reason': 'Empty or too-short name',
                'signals': signals,
            }
        
        if is_ui_action(name_lower):
            signals.append('ui_action_name')
            return {
                'entity_type': ENTITY_NOISE,
                'confidence': 0.95,
                'reason': f'Name is UI action: {name}',
                'signals': signals,
            }
        
        if is_platform_name(name_lower):
            signals.append('platform_name')
            return {
                'entity_type': ENTITY_NOISE,
                'confidence': 0.95,
                'reason': f'Name is platform name: {name}',
                'signals': signals,
            }
        
        # Check for notification/feed noise patterns
        NOISE_PATTERNS = [
            r'^\d+\s+(new|unread|notification|update|result)',
            r'(accepted your|sent you|shared a|reacted to)',
            r'^(sign in|join now|log in|sign up|create account)',
            r'^(see all|show more|load more|view all|more results)',
            r'^(cookie|privacy|terms|disclaimer)',
            # CTA / promotional / marketing noise
            r'^(unlock|discover|explore|learn more|get started|try|start|find out|check out)\b.{5,}',
            r'\b(insights? on|insights? about|insights? for|insights? into)\b',
            r'^(sponsored|promoted|advertisement|ad)\b',
            r'^(subscribe|follow us|join us|connect with us)',
            r'^(trending|popular|recommended|suggested)\b',
            r'^(premium|upgrade|pro plan|free trial)\b',
            # Feed / activity noise
            r'^(feed post|more groups|people also viewed|people you may know)',
            r'^(liked by|commented on|shared by|posted by)\b',
            r'^(add to|remove from|save to|bookmark)\b',
            r'\b(?:current openings|job openings|career opportunities|latest openings)\b',
            # Chat presence, activity status & system indicators
            r'\b(?:status is (?:offline|online|away|busy|available|dnd|inactive)|active (?:now|\d+m ago)|(?:last|recently) seen)\b',
            # Social / company profile counts & aggregated indicators
            r'^\d+\s+(?:associated\s+members?|employees?|alumni|followers?|connections?|members?)\b',
        ]
        for pat in NOISE_PATTERNS:
            if re.search(pat, name_lower):
                signals.append(f'noise_pattern:{pat}')
                return {
                    'entity_type': ENTITY_NOISE,
                    'confidence': 0.95,
                    'reason': f'Name matches noise pattern: {name}',
                    'signals': signals,
                }
        
        # Check for names that are too long to be a person or company (likely sentences/descriptions)
        # Market signals can be 6-7 words (e.g. 'Tech Hiring Surge in Q3 2026')
        word_count = len(name.split())
        if word_count >= 8:
            signals.append('sentence_length_name')
            return {
                'entity_type': ENTITY_NOISE,
                'confidence': 0.90,
                'reason': f'Name is too long ({word_count} words), likely a description: {name}',
                'signals': signals,
            }

        # Check for URL / domain / search snippet noise
        if re.search(r'(?:https?://|www\.|httpswww|\.com/|\.org/|\.net/|\.io/|zhihu\.com|youtube\.com|instagram\.com|justanswer\.com|microsoft\.com|hindustantimes)', name_lower):
            signals.append('url_or_web_snippet_noise')
            return {
                'entity_type': ENTITY_NOISE,
                'confidence': 1.0,
                'reason': f'Name contains URL or search snippet artifacts: {name}',
                'signals': signals,
            }

        return None
    
    def _check_company(self, name, name_lower, title, title_lower, company, email, url, page_title, signals) -> Optional[Dict]:
        """Detect company/organization entities."""
        from ..utils.normalizer import is_company_name, is_company_industry, validate_human_name
        
        # GUARD: If the name is definitively a valid human name and does NOT have explicit corporate markers,
        # it cannot be a company even if viewed on a company page / feed!
        is_human, clean_hname, _ = validate_human_name(name)
        if is_human and not is_company_name(name):
            return None

        confidence = 0.0
        reasons = []
        
        # Signal 1: Name is recognized as company
        if is_company_name(name):
            confidence += 0.50
            reasons.append('name matches company patterns')
            signals.append('company_name_detected')
        
        # Signal 2: Source URL is a company page
        if url and '/company/' in url:
            confidence += 0.25
            reasons.append('URL is /company/ path')
            signals.append('company_url')
        
        # Signal 3: Page title indicates company page
        if page_title and any(p in page_title for p in [': overview', ': people', ': jobs', 'company profile', 'about us', 'our team']):
            confidence += 0.15
            reasons.append('page title indicates company page')
            signals.append('company_page_title')
        
        # Signal 4: Title is an industry descriptor (not a job title)
        if title and is_company_industry(title):
            confidence += 0.15
            reasons.append('title is industry descriptor')
            signals.append('industry_title')
        
        # Signal 5: Email is a generic role address (info@, contact@, careers@)
        if email:
            GENERIC_PREFIXES = {'info', 'contact', 'careers', 'jobs', 'hr', 'recruiting', 'admin', 'support', 'sales', 'marketing', 'media', 'press', 'billing', 'office', 'team', 'general', 'reception', 'help'}
            local_part = email.split('@')[0] if '@' in email else ''
            if local_part.lower() in GENERIC_PREFIXES:
                confidence += 0.20
                reasons.append(f'generic role email prefix: {local_part}')
                signals.append('generic_email')
        
        # Signal 6: Name contains TLD (e.g. 'Beacontechinc.Com')
        if re.search(r'\.(com|net|org|io|co|biz|info|edu|gov)\b', name_lower, re.IGNORECASE):
            confidence += 0.30
            reasons.append('name contains TLD')
            signals.append('tld_in_name')
        
        # Signal 7: No individual contact details + company URL structure
        if not email and not company and url and ('/company/' in url or '/about' in url or '/team' in url or '/contact' in url):
            confidence += 0.10
            reasons.append('no individual contact + company URL')
            signals.append('no_individual_signals')
        
        if confidence >= 0.40:
            return {
                'entity_type': ENTITY_COMPANY,
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons),
                'signals': signals,
            }
        
        return None
    
    def _check_job_posting(self, name, name_lower, title, title_lower, url, page_title, signals) -> Optional[Dict]:
        """Detect job posting / vacancy entities."""
        from ..utils.normalizer import is_job_posting_title
        
        confidence = 0.0
        reasons = []
        
        # Signal 1: Name itself is a job posting title
        if is_job_posting_title(name_lower):
            confidence += 0.50
            reasons.append('name is a job posting title')
            signals.append('job_title_as_name')
        
        # Signal 2: URL indicates job page
        JOB_URL_PATTERNS = ['/jobs/', '/job/', '/career', '/vacancy', '/opening', '/apply/', '/position/']
        if url and any(p in url for p in JOB_URL_PATTERNS):
            confidence += 0.25
            reasons.append('URL indicates job listing page')
            signals.append('job_url')
        
        # Signal 3: Page title indicates job listing
        if page_title and any(p in page_title for p in ['job listing', 'job opening', 'career opportunity', 'hiring', 'apply now', 'job description']):
            confidence += 0.15
            reasons.append('page title indicates job listing')
            signals.append('job_page_title')
        
        # Signal 4: Name contains hiring-specific keywords
        JOB_KEYWORDS = ['hiring', 'we are hiring', 'now hiring', 'job opening', 'vacancy', 'position available', 'apply now', 'immediate opening']
        if any(kw in name_lower for kw in JOB_KEYWORDS):
            confidence += 0.30
            reasons.append('name contains hiring keywords')
            signals.append('hiring_keywords')
        
        if confidence >= 0.40:
            return {
                'entity_type': ENTITY_JOB_POSTING,
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons),
                'signals': signals,
            }
        
        return None
    
    def _check_contact_info(self, name, name_lower, title_lower, email, phone, url, signals) -> Optional[Dict]:
        """Detect generic contact page data (org email/phone without person identity)."""
        confidence = 0.0
        reasons = []
        
        # Check if name is a generic role descriptor
        GENERIC_CONTACT_NAMES = {
            'contact', 'contact us', 'get in touch', 'reach us', 'customer service',
            'support team', 'help desk', 'reception', 'front desk', 'switchboard',
            'main office', 'headquarters', 'general inquiries', 'general inquiry',
            'support team desk', 'service desk', 'helpdesk',
        }
        GENERIC_SUBSTRINGS = (
            'support team', 'help desk', 'team desk', 'support desk', 'customer service',
            'front desk', 'service desk', 'general inquiries', 'contact us', 'get in touch'
        )
        if name_lower in GENERIC_CONTACT_NAMES or any(sub in name_lower for sub in GENERIC_SUBSTRINGS):
            confidence += 0.50
            reasons.append(f'generic contact name: {name}')
            signals.append('generic_contact_name')
        
        # Check title
        if title_lower in ('contact', 'contact us', 'general contact', 'main contact', 'office contact'):
            confidence += 0.20
            reasons.append('generic contact title')
            signals.append('generic_contact_title')
        
        # Has email or phone but name is not a person
        if (email or phone) and confidence > 0:
            confidence += 0.15
            reasons.append('has contact details with generic identity')
            signals.append('contact_with_generic_identity')
        
        # Contact page URL
        if url and any(p in url for p in ['/contact', '/reach-us', '/get-in-touch']):
            confidence += 0.10
            reasons.append('contact page URL')
            signals.append('contact_url')
        
        if confidence >= 0.40:
            return {
                'entity_type': ENTITY_CONTACT_INFO,
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons),
                'signals': signals,
            }
        
        return None
    
    def _check_market_signal(self, name, name_lower, title, title_lower, url, page_title, signals) -> Optional[Dict]:
        """Detect market intelligence, hiring signals, industry trends."""
        confidence = 0.0
        reasons = []
        
        # Hiring trend patterns
        SIGNAL_PATTERNS = [
            r'hiring (\d+|surge|trend|freeze|spree)',
            r'(layoffs?|restructuring|downsizing|expansion)',
            r'(market (report|analysis|trend|outlook))',
            r'(industry (report|analysis|trend|outlook|news))',
            r'(salary (survey|data|report|guide))',
            r'(workforce (report|trend|data|planning))',
        ]
        for pat in SIGNAL_PATTERNS:
            if re.search(pat, name_lower):
                confidence += 0.40
                reasons.append(f'matches market signal pattern')
                signals.append(f'signal_pattern:{pat}')
                break
        
        # News/report page indicators
        if page_title and any(p in page_title for p in ['press release', 'news', 'blog', 'report', 'whitepaper', 'research']):
            confidence += 0.15
            reasons.append('news/report page title')
            signals.append('news_page')
        
        if confidence >= 0.40:
            return {
                'entity_type': ENTITY_MARKET_SIGNAL,
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons),
                'signals': signals,
            }
        
        return None


# Singleton instance
entity_classifier = EntityTypeClassifier()
