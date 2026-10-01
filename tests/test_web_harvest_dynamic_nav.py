"""
tests/test_web_harvest_dynamic_nav.py — Verification for Dynamic Nav Link Discovery
"""

import pytest
from backend.app.services.web_harvest_engine import web_harvest_engine


def test_dynamic_nav_link_extraction():
    html = """
    <header>
      <nav>
        <a href="/about-us">About Us</a>
        <a href="/company/leadership-team">Executive Leadership</a>
        <a href="/our-people">Our People</a>
        <a href="https://myco.com/board-of-directors">Board</a>
        <a href="/careers">Careers & Openings</a>
        <a href="/privacy-policy">Privacy</a>
        <a href="https://external.com/team">Partner Team</a>
        <a href="#main-content">Skip</a>
      </nav>
    </header>
    """
    discovered = web_harvest_engine._extract_team_links_from_html(html, "myco.com")

    assert "/about-us" in discovered
    assert "/company/leadership-team" in discovered
    assert "/our-people" in discovered
    assert "/board-of-directors" in discovered
    assert "/careers" not in discovered
    assert "/privacy-policy" not in discovered
    assert "#main-content" not in discovered
    assert "https://external.com/team" not in discovered


def test_empty_or_malformed_html():
    assert web_harvest_engine._extract_team_links_from_html("", "myco.com") == []
    assert web_harvest_engine._extract_team_links_from_html("<div>No links</div>", "myco.com") == []
