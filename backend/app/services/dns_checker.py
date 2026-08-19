"""
TalentOpsAI - Sender Domain DNS & Deliverability Health Inspector
================================================================
Performs live DNS audits on outreach sending domains:
  - SPF (Sender Policy Framework) record discovery & syntax check
  - DMARC (Domain-based Message Authentication) policy inspection
  - MX (Mail Exchange) routing validation
  - DKIM (DomainKeys Identified Mail) selector probes
  - Comprehensive Deliverability Health Score (0-100) & Fix Guidance
"""

import socket
import logging
from typing import Dict, Any, List

logger = logging.getLogger("talentops.dns_checker")

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class DomainHealthChecker:
    COMMON_DKIM_SELECTORS = ["google", "k1", "selector1", "s1", "default", "smtp", "mail", "mandrill", "sendgrid", "zoho"]

    def inspect_domain(self, domain_or_email: str) -> Dict[str, Any]:
        """
        Inspects the domain extracted from email or bare domain.
        """
        domain = domain_or_email.strip().lower()
        if "@" in domain:
            domain = domain.split("@")[-1].strip()

        # Sanitize
        domain = domain.replace("http://", "").replace("https://", "").split("/")[0].strip()

        report = {
            "domain": domain,
            "has_mx": False,
            "mx_records": [],
            "has_spf": False,
            "spf_record": None,
            "spf_status": "Missing",
            "has_dmarc": False,
            "dmarc_record": None,
            "dmarc_policy": None,
            "dmarc_status": "Missing",
            "dkim_selectors_found": [],
            "health_score": 0,
            "risk_tier": "high",
            "recommendations": []
        }

        if not domain or "." not in domain:
            report["recommendations"].append("Invalid domain format provided.")
            return report

        # 1. Inspect MX Records
        mx_records = self._get_mx_records(domain)
        if mx_records:
            report["has_mx"] = True
            report["mx_records"] = mx_records
        else:
            report["recommendations"].append("No MX records found. Emails cannot be delivered to or from this domain.")

        # 2. Inspect SPF (TXT records on root domain)
        txt_records = self._get_txt_records(domain)
        for txt in txt_records:
            if "v=spf1" in txt:
                report["has_spf"] = True
                report["spf_record"] = txt
                if "~all" in txt or "-all" in txt:
                    report["spf_status"] = "Strict / Enforced"
                elif "?all" in txt:
                    report["spf_status"] = "Neutral (Weak)"
                    report["recommendations"].append("SPF ends in '?all' (neutral). Recommend upgrading to '~all' (softfail) or '-all' (fail).")
                else:
                    report["spf_status"] = "Configured"
                break

        if not report["has_spf"]:
            report["recommendations"].append("Missing SPF record. Add 'v=spf1 include:_spf.google.com ~all' (or your provider's SPF) to TXT.")

        # 3. Inspect DMARC (TXT record on _dmarc.domain)
        dmarc_txts = self._get_txt_records(f"_dmarc.{domain}")
        for txt in dmarc_txts:
            if "v=DMARC1" in txt:
                report["has_dmarc"] = True
                report["dmarc_record"] = txt
                # Extract policy
                parts = [p.strip() for p in txt.split(";")]
                for p in parts:
                    if p.startswith("p="):
                        report["dmarc_policy"] = p.split("=")[1].strip()
                        break
                if report["dmarc_policy"] in ("reject", "quarantine"):
                    report["dmarc_status"] = f"Strong ({report['dmarc_policy']})"
                else:
                    report["dmarc_status"] = f"Monitoring ({report['dmarc_policy'] or 'none'})"
                break

        if not report["has_dmarc"]:
            report["recommendations"].append("Missing DMARC record. Create a TXT record at '_dmarc." + domain + "' with 'v=DMARC1; p=none; sp=none;'.")

        # 4. Probe common DKIM selectors
        for selector in self.COMMON_DKIM_SELECTORS:
            dkim_domain = f"{selector}._domainkey.{domain}"
            dkim_txts = self._get_txt_records(dkim_domain)
            for txt in dkim_txts:
                if "v=DKIM1" in txt or "k=rsa" in txt or "p=" in txt:
                    report["dkim_selectors_found"].append({"selector": selector, "record": txt[:45] + "..."})
                    break

        # Compute Deliverability Health Score
        score = 0
        if report["has_mx"]:
            score += 30
        if report["has_spf"]:
            score += 35
            if report["spf_status"] == "Strict / Enforced":
                score += 5
        if report["has_dmarc"]:
            score += 25
            if report["dmarc_policy"] in ("quarantine", "reject"):
                score += 5
        if len(report["dkim_selectors_found"]) > 0:
            score = min(100, score + 10)

        report["health_score"] = min(100, score)

        if report["health_score"] >= 80:
            report["risk_tier"] = "low"
            report["status_label"] = "Excellent (Ready for Cold Outreach)"
        elif report["health_score"] >= 50:
            report["risk_tier"] = "medium"
            report["status_label"] = "Moderate Risk (Some Auth Missing)"
        else:
            report["risk_tier"] = "high"
            report["status_label"] = "High Risk (Likely to Land in Spam)"

        return report

    def _get_mx_records(self, domain: str) -> List[str]:
        if DNS_AVAILABLE:
            try:
                answers = dns.resolver.resolve(domain, 'MX', lifetime=3.0)
                return [str(r.exchange).rstrip('.') for r in answers]
            except Exception:
                pass
        # Fallback socket lookup
        try:
            host, aliases, ips = socket.gethostbyname_ex(domain)
            return [host] if host else []
        except Exception:
            return []

    def _get_txt_records(self, domain: str) -> List[str]:
        if DNS_AVAILABLE:
            try:
                answers = dns.resolver.resolve(domain, 'TXT', lifetime=3.0)
                results = []
                for r in answers:
                    for item in r.strings:
                        results.append(item.decode('utf-8', errors='ignore'))
                return results
            except Exception:
                pass
        return []


domain_health_checker = DomainHealthChecker()
