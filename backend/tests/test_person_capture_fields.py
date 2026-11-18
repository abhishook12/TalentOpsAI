import json
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.models import Company, Recruiter
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.services import ingestion_funnel


def test_person_capture_to_saved_record(monkeypatch):
    engine = create_engine("sqlite://")
    Company.__table__.create(engine)
    Recruiter.__table__.create(engine)
    monkeypatch.setattr(ingestion_funnel.smtp_prober, "probe_mailbox",
                        lambda email: SimpleNamespace(smtp_code=250))
    funnel = ingestion_funnel.UniversalIngestionFunnel()

    def capture(name, slug, company, title, location):
        url = f"https://www.linkedin.com/in/{slug}/"
        return DiscoveryStaging(raw_name=name, raw_company=company, raw_title=title,
                                raw_location=location, source_url=url, raw_linkedin=url,
                                capture_id="test-frame", raw_email=f"{slug}@fixture.invalid",
                                source_page_title=f"{name} | LinkedIn")

    with Session(engine) as db:
        anjan = capture("Anjan Chowdhury", "anjan-chowdhury", "Technoy",
                        "Sr. Engineering manager @Myntra | EX OLA, GOOMO",
                        "Bengaluru, Karnataka, India · Contact info")
        result = funnel.process_staging_record(anjan, db)
        assert result["status"] == "PROMOTED", result
        db.commit()
        saved = db.get(Recruiter, result["recruiter_id"])
        assert saved.company.company_name == "Myntra"
        assert saved.location == "Bengaluru, Karnataka, India"
        evidence = json.loads(saved.metadata_json)["person_field_evidence"]
        assert evidence["employer"]["section"] == "headline"
        assert evidence["location"]["capture_id"] == "test-frame"

        morgan = capture("Morgan Arakelian", "morgan-arakelian",
                         "Our Team - Daley and Associates", "Data Analyst", "Remote")
        result = funnel.process_staging_record(morgan, db)
        assert result["status"] == "PROMOTED", result
        db.commit()
        saved = db.get(Recruiter, result["recruiter_id"])
        assert saved.company_id is None and saved.location is None
        morgan.raw_company = "Daley and Associates"
        morgan.raw_location = "Boston, Massachusetts"
        assert funnel.process_staging_record(morgan, db)["status"] == "ENRICHED"
        db.commit()
        assert saved.company.company_name == "Daley and Associates"
        assert saved.location == "Boston, Massachusetts"
        morgan.raw_company = None
        morgan.raw_location = "Remote"
        assert funnel.process_staging_record(morgan, db)["status"] == "ENRICHED"
        db.commit()
        assert saved.location == "Boston, Massachusetts"
        assert saved.company.company_name == "Daley and Associates"
        morgan.raw_company = "Globex Corporation"
        assert funnel.process_staging_record(morgan, db)["status"] == "HELD_REVIEW"
        db.commit()
        assert saved.company.company_name == "Daley and Associates"
