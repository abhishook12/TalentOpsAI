import pytest
from scout_desktop.extractor.patterns import (
    classify_semantic_entity,
    is_valid_person_name,
    is_valid_company_name,
)

class TestSemanticEntityDiscrimination:
    """
    Authoritative test suite verifying mutual exclusivity and 100% precision
    between PERSON, COMPANY, SECTION_HEADER, WORKPLACE_TYPE, EDUCATION,
    SKILL, DEPARTMENT_OR_INDUSTRY, JOB_TITLE, LOCATION, and UI_NOISE.
    """

    @pytest.mark.parametrize("name", [
        "Abhishek Jadon",
        "Mohit Tiwari",
        "Satya Nadella",
        "Sundar Pichai",
        "Tim Cook",
        "John Smith",
        "David A. Sinclair",
        "Ludwig van Beethoven",
        "Kate Threewitts",
        "Megan Alford",
        "Alexandra Fotos",
        "Jennifer Kurilko",
        "Emily R. Thorne",
    ])
    def test_person_names_classified_as_person(self, name):
        res = classify_semantic_entity(name)
        assert res["entity_type"] == "PERSON", f"Failed for {name}: {res}"
        assert is_valid_person_name(name) is True

    @pytest.mark.parametrize("company", [
        "Tek Inspirations",
        "Kochar Tech",
        "Google",
        "Microsoft",
        "Amazon Web Services",
        "Figma",
        "Stripe",
        "Docker",
        "Cambridge Advisors",
        "Management Consultants Inc",
        "Senior Advisor Group",
        "Level 3",
        "Factor 75",
        "8x8",
        "3M",
        "Acme Corp",
        "Cloud Destinations LLC",
        "KPMG",
        "HSBC",
        "CBRE",
        "InnovaWorkforce Inc",
        "Tata Consultancy Services",
        "Cognizant",
        "Apex Systems",
    ])
    def test_companies_classified_as_company(self, company):
        res = classify_semantic_entity(company)
        assert res["entity_type"] == "COMPANY", f"Failed for {company}: {res}"
        assert is_valid_company_name(company) is True

    @pytest.mark.parametrize("header", [
        "Experience",
        "Work Experience",
        "Education",
        "About",
        "Overview",
        "Skills",
        "Top Skills",
        "Projects",
        "Certifications",
        "Recommendations",
        "Summary",
        "Languages",
        "Interests",
        "Honors & Awards",
    ])
    def test_section_headers_classified_as_section_header(self, header):
        res = classify_semantic_entity(header)
        assert res["entity_type"] == "SECTION_HEADER", f"Failed for {header}: {res}"

    @pytest.mark.parametrize("wp", [
        "Full-time",
        "Part-time",
        "Contract",
        "Contractor",
        "Hybrid",
        "Remote",
        "On-site",
        "Internship",
        "Freelance",
        "Apprenticeship",
    ])
    def test_workplace_types_classified_as_workplace_type(self, wp):
        res = classify_semantic_entity(wp)
        assert res["entity_type"] == "WORKPLACE_TYPE", f"Failed for {wp}: {res}"

    @pytest.mark.parametrize("edu", [
        "Stanford University",
        "Harvard University",
        "Massachusetts Institute of Technology",
        "UC Berkeley",
        "B.S. Computer Science",
        "Master of Business Administration",
        "Ph.D.",
        "B.Tech",
        "M.S. Electrical Engineering",
    ])
    def test_education_classified_as_education(self, edu):
        res = classify_semantic_entity(edu)
        assert res["entity_type"] == "EDUCATION", f"Failed for {edu}: {res}"

    @pytest.mark.parametrize("skill", [
        "Python",
        "Java",
        "Kubernetes",
        "PostgreSQL",
        "React",
        "TypeScript",
        "FastAPI",
        "Django",
        "Machine Learning",
        "GraphQL",
        "Terraform",
    ])
    def test_skills_classified_as_skill(self, skill):
        res = classify_semantic_entity(skill)
        assert res["entity_type"] == "SKILL", f"Failed for {skill}: {res}"

    @pytest.mark.parametrize("dept", [
        "Human Resources",
        "Information Technology",
        "Quality Assurance",
        "Talent Acquisition",
        "Legal Services",
        "Finance & Accounting",
        "Software Engineering",
    ])
    def test_departments_classified_as_department(self, dept):
        res = classify_semantic_entity(dept)
        assert res["entity_type"] == "DEPARTMENT_OR_INDUSTRY", f"Failed for {dept}: {res}"

    @pytest.mark.parametrize("title", [
        "Senior Software Engineer",
        "Recruiting Manager",
        "Chief Technology Officer",
        "VP of Sales",
        "Product Designer",
        "Data Scientist",
    ])
    def test_job_titles_classified_as_job_title(self, title):
        res = classify_semantic_entity(title)
        assert res["entity_type"] == "JOB_TITLE", f"Failed for {title}: {res}"

    @pytest.mark.parametrize("loc", [
        "San Francisco, CA",
        "Bengaluru, Karnataka",
        "New York, NY",
        "London, UK",
        "Austin, TX",
        "Seattle, WA",
    ])
    def test_locations_classified_as_location(self, loc):
        res = classify_semantic_entity(loc)
        assert res["entity_type"] == "LOCATION", f"Failed for {loc}: {res}"

    @pytest.mark.parametrize("noise", [
        "Open to work",
        "Save to PDF",
        "Connect",
        "Message",
        "500+ connections",
        "1st degree",
        "Accept cookies",
    ])
    def test_ui_noise_classified_as_ui_noise(self, noise):
        res = classify_semantic_entity(noise)
        assert res["entity_type"] == "UI_NOISE", f"Failed for {noise}: {res}"
