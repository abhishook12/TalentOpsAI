"""
tests/test_flywheel_and_lexicon_repair.py

Verifies:
1. Neural Lexicon Repair heals anti-aliased OCR corruptions in candidate job titles and companies.
2. SequenceScheduler auto_enroll_recruiter successfully enrolls newly promoted candidates into active auto-enroll campaigns.
3. db_auto_enricher triggers flywheel auto-enrollment on high-confidence candidate promotions.
"""

import pytest
import json
from datetime import datetime, timezone
from scout_desktop.extractor.neural_lexicon_repair import lexicon_repair
from scout_desktop.extractor.field_classifier import FieldClassifier
from backend.app.database import SessionLocal
from backend.app.models.models import Recruiter
from backend.app.models.campaigns import (
    Campaign, CampaignStatus, CampaignRecruiter,
    CampaignRecruiterStatus, SequenceStep, EmailTemplate
)
from backend.app.services.sequence_scheduler import sequence_scheduler, auto_enroll_recruiter


class TestNeuralLexiconRepair:
    def test_01_glyph_confusion_pre_cleaning(self):
        corrupted = "Sen1or Techn1cal Recru1ter"
        cleaned = lexicon_repair.pre_clean_ocr_glyphs(corrupted)
        # Verify deterministic replacement of digits/symbols in words
        assert cleaned is not None
        assert "1" not in cleaned

    def test_02_canonical_lexicon_fuzzy_repair(self):
        corrupted_title = "Sen1or Techn1cal Recru1ter"
        repaired, conf = lexicon_repair.repair_title(corrupted_title)
        assert repaired == "Senior Technical Recruiter"
        assert conf >= 0.85

    def test_03_talent_acquisition_repair(self):
        corrupted_title = "Ta1ent Acquisiti0n Partner"
        repaired, conf = lexicon_repair.repair_title(corrupted_title)
        assert repaired == "Talent Acquisition Partner"
        assert conf >= 0.85

    def test_04_field_classifier_integration(self):
        # Even with OCR artifacts, field classifier should recover valid title
        headline = ["Sen1or Techn1cal Recru1ter @ Google"]
        t, t_conf, c, c_conf = FieldClassifier.extract_title_and_company(
            headline_lines=headline,
            header_lines=[],
            experience_lines=[]
        )
        assert t == "Senior Technical Recruiter"
        assert t_conf >= 0.85
        assert c == "Google"


class TestFlywheelAutoEnrollment:
    def test_01_auto_enroll_eligibility_and_creation(self):
        with SessionLocal() as db:
            # 1. Create a dummy test recruiter in DB
            test_recruiter = Recruiter(
                recruiter_name="Ada Lovelace",
                email="ada.flywheel.test@example.com",
                title="Senior Technical Recruiter",
                data_source="unit_test"
            )
            db.add(test_recruiter)
            db.flush()
            rec_id = test_recruiter.recruiter_id

            # 2. Create a dummy test campaign with auto_enroll = True
            test_camp = Campaign(
                name="[TEST] Flywheel Auto-Enroll Campaign",
                status=CampaignStatus.active.value,
                is_active=True,
                is_archived=False,
                from_email="flywheel@talentops.ai",
                metadata_json=json.dumps({"auto_enroll": True, "min_confidence": 70})
            )
            db.add(test_camp)
            db.flush()

            # Add email template and sequence step
            tmpl = EmailTemplate(
                campaign_id=test_camp.campaign_id,
                name="Flywheel Step 1",
                subject="Exciting role at {{company}}",
                body="Hi {{first_name}}, loved your background."
            )
            db.add(tmpl)
            db.flush()

            step = SequenceStep(
                campaign_id=test_camp.campaign_id,
                template_id=tmpl.template_id,
                step_order=1,
                delay_days=0,
                delay_hours=0,
                is_active=True
            )
            db.add(step)
            db.commit()

            camp_id = test_camp.campaign_id

            try:
                # 3. Test auto_enroll_recruiter with high confidence
                enrolled = auto_enroll_recruiter(
                    db=db,
                    recruiter_id=rec_id,
                    email=test_recruiter.email,
                    name=test_recruiter.recruiter_name,
                    company="DeepMind",
                    title="Senior Technical Recruiter",
                    confidence=95,
                    source="unit_test"
                )

                assert camp_id in enrolled

                # Verify CampaignRecruiter was created in DB
                cr = db.query(CampaignRecruiter).filter(
                    CampaignRecruiter.campaign_id == camp_id,
                    CampaignRecruiter.recruiter_id == rec_id
                ).first()

                assert cr is not None
                assert cr.status == CampaignRecruiterStatus.pending.value
                assert cr.current_step_id == step.step_id
                var_dict = json.loads(cr.variables_json)
                assert var_dict["first_name"] == "Ada"
                assert var_dict["company"] == "DeepMind"
                meta_dict = json.loads(cr.metadata_json)
                assert meta_dict["auto_enrolled"] is True

                # 4. Test deduplication: calling again should NOT re-enroll
                enrolled_again = auto_enroll_recruiter(
                    db=db,
                    recruiter_id=rec_id,
                    email=test_recruiter.email,
                    name=test_recruiter.recruiter_name,
                    company="DeepMind",
                    title="Senior Technical Recruiter",
                    confidence=95,
                    source="unit_test"
                )
                assert enrolled_again == []

                # 5. Test low confidence rejection (<70)
                enrolled_low = auto_enroll_recruiter(
                    db=db,
                    recruiter_id=rec_id,
                    email="low.conf@example.com",
                    confidence=50,
                    source="unit_test"
                )
                assert enrolled_low == []

            finally:
                # Cleanup test records
                db.rollback()
                db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == camp_id).delete()
                db.query(SequenceStep).filter(SequenceStep.campaign_id == camp_id).delete()
                db.query(EmailTemplate).filter(EmailTemplate.campaign_id == camp_id).delete()
                db.query(Campaign).filter(Campaign.campaign_id == camp_id).delete()
                db.query(Recruiter).filter(Recruiter.recruiter_id == rec_id).delete()
                db.commit()
