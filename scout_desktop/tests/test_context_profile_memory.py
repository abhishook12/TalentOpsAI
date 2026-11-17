from scout_desktop.core.context_memory import ContextMemory


def test_context_memory_merges_profile_sections_without_cross_field_loss():
    memory = ContextMemory()
    memory.update_page_context("PERSON_PROFILE", "https://www.linkedin.com/in/example", "LINKEDIN")
    entity = memory.register_entity("person-1", "PERSON", "Example Person", "https://www.linkedin.com/in/example")

    memory.update_entity_field(entity.entity_id, "HAS_TITLE", "Principal Consultant", "HAS_TITLE")
    memory.update_entity_field(entity.entity_id, "WORKS_AT", "Morgan McKinley", "WORKS_AT")
    memory.update_entity_field(entity.entity_id, "LOCATED_IN", "Cork, County Cork, Ireland", "LOCATED_IN")
    memory.update_entity_field(entity.entity_id, "STUDIED_AT", "University College Cork", "STUDIED_AT")
    memory.update_entity_field(entity.entity_id, "HAS_ABOUT_SUMMARY", "Recruitment specialist", "HAS_ABOUT_SUMMARY")
    memory.update_entity_field(entity.entity_id, "HAS_SKILL", "Recruiting", "HAS_SKILL")
    memory.update_entity_field(entity.entity_id, "HAS_SKILL", "ERP", "HAS_SKILL")

    enriched = memory.enrich_staged_profile(entity.entity_id, {"recruiter_name": "Example Person"})
    assert enriched["title"] == "Principal Consultant"
    assert enriched["company_name"] == "Morgan McKinley"
    assert enriched["location"] == "Cork, County Cork, Ireland"
    assert enriched["education"] == "University College Cork"
    assert enriched["about_summary"] == "Recruitment specialist"
    assert enriched["skills"] == ["Recruiting", "ERP"]
    assert "current_title" not in memory.get_information_gaps(entity.entity_id)
    assert "current_company" not in memory.get_information_gaps(entity.entity_id)


def test_context_memory_resets_between_profiles():
    memory = ContextMemory()
    memory.update_page_context("PERSON_PROFILE", "https://www.linkedin.com/in/first", "LINKEDIN")
    entity = memory.register_entity("person-1", "PERSON", "First Person", "https://www.linkedin.com/in/first")
    memory.update_entity_field(entity.entity_id, "WORKS_AT", "First Company", "WORKS_AT")

    memory.update_page_context("PERSON_PROFILE", "https://www.linkedin.com/in/second", "LINKEDIN")
    assert memory.get_primary_entity() is None
