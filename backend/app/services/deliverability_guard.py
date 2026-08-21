import re
from typing import Dict, List, Any, Optional

SPAM_KEYWORDS = {
    'urgency': [
        'act now', 'apply today', 'urgent', "don't miss", 'immediate response', 'expires',
        'limited time', 'call now', 'instant', 'once in a lifetime', 'hurry'
    ],
    'financial': [
        '100% free', 'guaranteed', 'earn $$$', 'cash bonus', 'no risk', 'pure profit',
        'make money', 'fast cash', 'million dollars', 'risk free', 'unsecured credit',
        'refinance', 'work from home $$', 'crypto investment'
    ],
    'deceptive_aggressive': [
        'click here', 'click below', 'open immediately', 'winner', 'congratulations',
        "you have been selected", 'as seen on', 'dear friend', "this isn't spam",
        'not spam', 'opt in', 'no catch', 'cancel anytime'
    ],
    'overpromising': [
        'miracle', 'revolutionary', 'guarantee success', 'double your income', 'unlimited leads',
        'no experience necessary', 'be your own boss'
    ]
}

class DeliverabilityGuard:
    def __init__(self):
        self.spam_keywords = SPAM_KEYWORDS

    def analyze_content(self, subject: str = "", body: str = "") -> Dict[str, Any]:
        combined_text = f"{subject or ''} {body or ''}".lower()
        clean_text = re.sub(r'<[^>]+>', ' ', combined_text)
        
        matches = []
        category_hits = {}
        
        for category, words in self.spam_keywords.items():
            for word in words:
                pattern = r'\b' + re.escape(word) + r'\b'
                found = re.findall(pattern, clean_text)
                if found:
                    matches.append({'keyword': word, 'category': category, 'count': len(found)})
                    category_hits[category] = category_hits.get(category, 0) + len(found)

        penalty = 0
        for cat, count in category_hits.items():
            if cat == 'financial':
                penalty += count * 15
            elif cat == 'deceptive_aggressive':
                penalty += count * 12
            elif cat == 'urgency':
                penalty += count * 8
            else:
                penalty += count * 10

        if subject:
            uppercase_chars = sum(1 for c in subject if c.isupper())
            total_chars = max(len(subject), 1)
            if uppercase_chars / total_chars > 0.4:
                penalty += 20
                matches.append({'keyword': 'EXCESSIVE_CAPS', 'category': 'formatting', 'count': 1})

        excessive_symbols = len(re.findall(r'[!?$]{2,}', f"{subject} {body}"))
        if excessive_symbols > 0:
            penalty += excessive_symbols * 8
            matches.append({'keyword': 'EXCESSIVE_SYMBOLS', 'category': 'formatting', 'count': excessive_symbols})

        spam_score = min(penalty, 100)
        deliverability_score = max(100 - spam_score, 0)

        if deliverability_score >= 85:
            rating = 'Optimal'
            badge_color = 'green'
        elif deliverability_score >= 70:
            rating = 'Good'
            badge_color = 'blue'
        elif deliverability_score >= 50:
            rating = 'Needs Improvement'
            badge_color = 'yellow'
        else:
            rating = 'High Spam Risk'
            badge_color = 'red'

        suggestions = []
        if matches:
            keywords_list = [m['keyword'] for m in matches if m['keyword'] not in ('EXCESSIVE_CAPS', 'EXCESSIVE_SYMBOLS')]
            if keywords_list:
                suggestions.append(f"Consider replacing high-risk trigger phrases: {', '.join(keywords_list[:3])}")
        if any(m['keyword'] == 'EXCESSIVE_CAPS' for m in matches):
            suggestions.append("Reduce excessive capitalization in subject line.")
        if any(m['keyword'] == 'EXCESSIVE_SYMBOLS' for m in matches):
            suggestions.append("Avoid repeated exclamation marks (!!) or dollar signs ($$).")

        return {
            'deliverability_score': deliverability_score,
            'spam_score': spam_score,
            'rating': rating,
            'badge_color': badge_color,
            'issues_detected': len(matches),
            'matches': matches,
            'suggestions': suggestions
        }

    def calculate_warmup_quota(self, account_age_days: int) -> int:
        if account_age_days <= 1:
            return 10
        elif account_age_days <= 3:
            return 25
        elif account_age_days <= 7:
            return 50
        elif account_age_days <= 14:
            return 100
        else:
            return 250

    def generate_unsubscribe_headers(self, campaign_id: int, recipient_email: str, base_url: str = 'https://talentopsai-1.onrender.com') -> Dict[str, str]:
        unsub_url = f"{base_url}/api/campaigns/{campaign_id}/unsubscribe?email={recipient_email}"
        mailto_url = f"mailto:unsubscribe@talentops.ai?subject=unsubscribe_campaign_{campaign_id}_{recipient_email}"
        return {
            'List-Unsubscribe': f"<{unsub_url}>, <{mailto_url}>",
            'List-Unsubscribe-Post': "List-Unsubscribe=One-Click"
        }

    def check_bounce_circuit_breaker(self, sent_count: int, failed_count: int, max_fail_percent: float = 5.0) -> bool:
        total = sent_count + failed_count
        if total < 10:
            return False
        fail_pct = (failed_count / total) * 100
        return fail_pct > max_fail_percent

deliverability_guard = DeliverabilityGuard()
