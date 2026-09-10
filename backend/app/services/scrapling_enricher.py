"""Scrapling Autonomous Company and Email Pattern Enrichment Service."""
import re
import json
import logging
from typing import Dict, Optional, List

try:
    from scrapling import Fetcher
except ImportError:
    Fetcher = None

logger = logging.getLogger('talentops.scrapling_enricher')

class ScraplingEnricher:
    def __init__(self):
        self.fetcher = Fetcher() if Fetcher is not None else None

    def enrich_company(self, company_name: str, domain: Optional[str] = None) -> Dict:
        if not domain and company_name:
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            domain = f'{clean_name}.com'
        if not domain:
            return {'status': 'SKIPPED', 'reason': 'no_domain'}

        if not self.fetcher:
            return {'status': 'SKIPPED', 'reason': 'scrapling_not_installed', 'domain': domain}

        target_urls = [
            f'https://{domain}',
            f'https://{domain}/about',
            f'https://{domain}/contact',
            f'https://{domain}/team',
        ]
        enriched_data = {
            'domain': domain,
            'company_name': company_name,
            'phone': None,
            'email_pattern': None,
            'sample_emails': [],
            'status': 'SUCCESS',
        }
        for url in target_urls:
            try:
                res = self.fetcher.get(url, timeout=5)
                if res and getattr(res, 'status', None) == 200:
                    text = getattr(res, 'text', '')
                    phones = re.findall(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text)
                    if phones and not enriched_data["phone"]:
                        enriched_data["phone"] = phones[0]
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@' + re.escape(domain), text, re.IGNORECASE)
                    for em in emails:
                        if em.lower() not in enriched_data["sample_emails"]:
                            enriched_data["sample_emails"].append(em.lower())
            except Exception as e:
                logger.debug('Error fetching %s: %s', url, e)
        if enriched_data["sample_emails"]:
            sample = enriched_data["sample_emails"][0].split('@')[0]
            if '.' in sample:
                enriched_data["raw_pattern"] = 'first.last'
            else:
                enriched_data["raw_pattern"] = 'first_initial_last'
        return enriched_data

scrapling_enricher = ScraplingEnricher()
