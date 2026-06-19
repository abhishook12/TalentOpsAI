from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Company


BATCH_KEY = f"seed_company_domains_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

DOMAIN_SEEDS = [
    {"company_id": 1507, "company_name": "Akkodis", "website": "akkodis.com"},
    {"company_id": 948, "company_name": "Eclaro", "website": "eclaro.com", "email_pattern": "eclaroit.com"},
    {"company_id": 833, "company_name": "Brooksource", "website": "brooksource.com"},
    {"company_id": 25283, "company_name": "Sigconsult", "website": "sigconsult.com"},
    {"company_id": 41725, "company_name": "Randstad Technologies", "website": "randstadtechnologies.com"},
    {"company_id": 31651, "company_name": "Workday", "website": "workday.com"},
    {"company_id": 35, "company_name": "MicroAge", "website": "microage.com"},
    {"company_id": 1623, "company_name": "Medixteam", "website": "medixteam.com"},
    {"company_id": 803, "company_name": "Atrium Staffing", "website": "atriumstaff.com", "email_pattern": "atriumworks.com"},
    {"company_id": 2040, "company_name": "ITMMI", "website": "itmmi.com"},
    {"company_id": 3523, "company_name": "MCA Connect", "website": "mcaconnect.com"},
    {"company_id": 23489, "company_name": "Advantagetechnical", "website": "advantagetechnical.com"},
    {"company_id": 20697, "company_name": "prestigestaffing", "website": "prestigestaffing.com"},
    {"company_id": 35281, "company_name": "Systemoneservices", "website": "systemoneservices.com"},
    {"company_id": 48, "company_name": "Spinnaker Support", "website": "spinnakersupport.com"},
    {"company_id": 3521, "company_name": "iT1", "website": "it1.com"},
    {"company_id": 41, "company_name": "NexusTek", "website": "nexustek.com"},
    {"company_id": 26513, "company_name": "Kellyservices", "website": "kellyservices.com"},
    {"company_id": 37651, "company_name": "Turnberrysolutions", "website": "turnberrysolutions.com"},
    {"company_id": 28285, "company_name": "Guidehouse", "website": "guidehouse.com"},
    {"company_id": 41827, "company_name": "Vaco", "website": "vaco.com"},
    {"company_id": 42253, "company_name": "Actalent Services", "website": "actalentservices.com"},
    {"company_id": 23844, "company_name": "Addisongroup", "website": "addisongroup.com"},
    {"company_id": 367, "company_name": "The Intersect Group", "website": "theintersectgroup.com"},
    {"company_id": 41913, "company_name": "PDS Tech", "website": "pdstech.com"},
    {"company_id": 21489, "company_name": "Judge", "website": "judge.com"},
    {"company_id": 2858, "company_name": "Tandym Group", "website": "tandymgroup.com"},
    {"company_id": 39079, "company_name": "Idr-inc", "website": "idr-inc.com"},
    {"company_id": 59, "company_name": "VLCM", "website": "vlcm.com"},
    {"company_id": 42274, "company_name": "Optomi", "website": "optomi.com"},
    {"company_id": 3503, "company_name": "Cloudgaia", "website": "cloudgaia.com"},
    {"company_id": 26993, "company_name": "Beaconhillstaffing", "website": "beaconhillstaffing.com"},
    {"company_id": 803, "company_name": "Atrium Staffing", "email_pattern": "atriumstaffing.com"},
    {"company_id": 31337, "company_name": "ManTech", "website": "mantech.com"},
    {"company_id": 49970, "company_name": "Abacusservice", "website": "abacusservice.com"},
    {"company_id": 80, "company_name": "Lucas James Talent Partners", "website": "lucasjamestalent.com"},
    {"company_id": 40534, "company_name": "selectgroup", "website": "selectgroup.com"},
    {"company_id": 54, "company_name": "The Whole Group", "website": "thewholegroup.com"},
    {"company_id": 3508, "company_name": "CoreX Corp", "website": "corexcorp.com"},
    {"company_id": 49, "company_name": "SwitchThink Solutions", "website": "switchthink.com"},
    {"company_id": 1134, "company_name": "Levi, Ray & Shoup, Inc. (LRS)", "website": "lrs.com"},
    {"company_id": 1486, "company_name": "Associate Staffing", "website": "associatestaffingllc.com"},
    {"company_id": 49154, "company_name": "Sevensteprpo", "website": "sevensteprpo.com"},
    {"company_id": 3513, "company_name": "Empower Partnerships", "website": "empowerpartnerships.com"},
    {"company_id": 3501, "company_name": "Cactus Healthcare Resources", "website": "cactusr.com"},
]


def merge_metadata(existing_value: str | None, evidence: dict) -> str:
    metadata = {}
    if existing_value:
        try:
            parsed = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
            if isinstance(parsed, dict):
                metadata = dict(parsed)
        except Exception:
            metadata = {"raw_metadata": str(existing_value)}
    metadata["seed_company_domains"] = evidence
    return json.dumps(metadata, default=str)


def main() -> None:
    db = SessionLocal()
    try:
        updated = 0
        skipped_missing = 0
        skipped_name_mismatch = 0

        for seed in DOMAIN_SEEDS:
            company = db.query(Company).filter(Company.company_id == seed["company_id"]).first()
            if not company:
                skipped_missing += 1
                print(f"missing_company_id={seed['company_id']}")
                continue

            if seed["company_name"].lower() not in (company.company_name or "").lower():
                skipped_name_mismatch += 1
                print(
                    f"name_mismatch company_id={company.company_id} expected={seed['company_name']} actual={company.company_name}"
                )
                continue

            changed = False
            evidence = {
                "batch_key": BATCH_KEY,
                "before_website": company.website,
                "before_email_pattern": company.email_pattern,
            }

            website = seed.get("website")
            if website and company.website != website:
                company.website = website
                changed = True

            email_pattern = seed.get("email_pattern")
            if email_pattern and company.email_pattern != email_pattern:
                company.email_pattern = email_pattern
                changed = True

            if changed:
                evidence["after_website"] = company.website
                evidence["after_email_pattern"] = company.email_pattern
                company.metadata_json = merge_metadata(company.metadata_json, evidence)
                updated += 1
                print(
                    f"updated company_id={company.company_id} company_name={company.company_name} "
                    f"website={company.website} email_pattern={company.email_pattern}"
                )

        db.commit()
        print(f"updated_companies={updated}")
        print(f"skipped_missing={skipped_missing}")
        print(f"skipped_name_mismatch={skipped_name_mismatch}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
