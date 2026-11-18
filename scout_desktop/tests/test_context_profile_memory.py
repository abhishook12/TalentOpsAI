from scout_desktop.core.context_memory import ContextMemory


def test_partial_browser_profile_recovers_visible_header_fields_only():
    from scout_desktop.extractor.profile_frame_text import supplement_profile_text
    browser = ["Morgan Lane", "Senior Recruiter", "Connect"]
    image = ["Other tab", "Morgan Lane · 2nd", "Senior Recruiter", "Boston, Massachusetts",
             "Example Associates", "Example University", "More profiles for you", "Other Person"]
    result = supplement_profile_text(browser, image, "Morgan Lane")
    assert result.count("Senior Recruiter") == 1
    assert all(field in result for field in ("Boston, Massachusetts", "Example Associates", "Example University"))
    assert "Other Person" not in result and "Other tab" not in result
    assert supplement_profile_text(browser, image, "Someone Else") == browser


def test_supplement_profile_text_preserves_employer_and_school_order():
    """
    Inserting missing OCR lines must not scramble employer and school order.
    Fields extracted from each source must retain their natural order.
    """
    from scout_desktop.extractor.profile_frame_text import supplement_profile_text
    browser = ["Morgan Lane", "Senior Recruiter", "Example Associates", "Connect"]
    image = [
        "Morgan Lane · 2nd",
        "Senior Recruiter",
        "Example Associates",
        "Example University",
        "Boston, Massachusetts",
    ]
    result = supplement_profile_text(browser, image, "Morgan Lane")
    assert "Example Associates" in result
    assert "Example University" in result
    emp_idx = result.index("Example Associates")
    sch_idx = result.index("Example University")
    assert emp_idx < sch_idx, f"Employer (index {emp_idx}) must appear before school (index {sch_idx})"
    assert result.index("Senior Recruiter") < emp_idx, "Title must appear before employer"


def test_supplement_profile_text_recovers_school_beneath_education_heading():
    """
    Visible profile recovery must not truncate at the Education heading,
    preserving the institution name beneath it.
    """
    from scout_desktop.extractor.profile_frame_text import supplement_profile_text
    browser = ["Morgan Lane", "Senior Recruiter", "Connect"]
    image = [
        "Morgan Lane · 2nd",
        "Senior Recruiter",
        "Example Associates",
        "Education",
        "Example University",
        "More profiles for you",
        "Other Person",
    ]
    result = supplement_profile_text(browser, image, "Morgan Lane")
    assert "Example University" in result, "School beneath Education heading must be recovered"
    assert "Other Person" not in result, "External profiles must still be excluded"
    emp_idx = result.index("Example Associates")
    sch_idx = result.index("Example University")
    assert emp_idx < sch_idx, "Employer must precede school"


def test_two_people_on_one_page_do_not_share_employment_or_education():
    memory = ContextMemory()
    url = "https://example.org/our-team"
    first = memory.register_entity("a", "PERSON", "Alex Reed", url)
    first.update_field("current_company", "Example Associates")
    first.update_field("education", "Example University")
    assert memory.find_entity_by_name("Morgan Lane", "PERSON", url) is None
    second = memory.register_entity("b", "PERSON", "Morgan Lane", url)
    assert memory.find_entity_by_name("Morgan Lane", "PERSON", url) is second
    assert not second.known_fields
    assert memory.find_entity_by_name("Alex Reed", "PERSON", url) is first


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


def test_context_memory_keeps_same_name_profiles_separate_by_profile_url():
    memory = ContextMemory()
    first = memory.register_entity(
        "person-1", "PERSON", "Alex Kim", "https://www.linkedin.com/in/alex-kim-recruiting"
    )
    second = memory.register_entity(
        "person-2", "PERSON", "Alex Kim", "https://www.linkedin.com/in/alex-kim-engineering"
    )

    assert memory.find_entity_by_name(
        "Alex Kim", "PERSON", "https://www.linkedin.com/in/alex-kim-recruiting"
    ).entity_id == first.entity_id
    assert memory.find_entity_by_name(
        "Alex Kim", "PERSON", "https://www.linkedin.com/in/alex-kim-engineering"
    ).entity_id == second.entity_id
    assert memory.find_entity_by_name("Alex Kim", "PERSON") is None
