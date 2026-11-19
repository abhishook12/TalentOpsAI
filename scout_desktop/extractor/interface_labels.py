"""Identify interface labels that can appear inside captured person fields."""
import re


def interface_label(value):
    text = " ".join(str(value or "").casefold().split()).strip(" :.")
    return text in {
        "company", "company name", "management level", "city", "location",
        "select region", "select location", "select company", "select city",
        "ai assistant", "a1 assistant", "job title", "current title",
    } or bool(re.match(r"^(?:welcome,\s|your assistant is |you['’]ve selected |select a region\b)", text))
