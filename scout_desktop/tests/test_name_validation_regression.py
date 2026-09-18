import pytest
from scout_desktop.extractor.patterns import (
    is_valid_person_name,
    clean_person_name,
)

class TestPersonNameValidationRegression:
    def test_middle_initials(self):
        names = ["John F. Kennedy", "David A. Sinclair", "Mary J. Blige", "George W. Bush"]
        for n in names:
            cleaned = clean_person_name(n)
            assert cleaned is not None, f"clean returned None for: {n}"
            assert is_valid_person_name(cleaned) is True, f"is_valid failed for: {cleaned}"

    def test_particle_names(self):
        names = ["Guido van Rossum", "Vincent van Gogh", "Leonardo da Vinci", "Ludwig van Beethoven", "Simone de Beauvoir"]
        for n in names:
            cleaned = clean_person_name(n)
            assert cleaned is not None, f"clean returned None for: {n}"
            assert is_valid_person_name(cleaned) is True, f"is_valid failed for: {cleaned}"

    def test_unbanned_developer_names(self):
        names = ["Abhishek Sharma", "Gaurav Kumar", "Prashant Patel", "Tushar Gupta", "Muskan Verma", "Yatendra Singh"]
        for n in names:
            cleaned = clean_person_name(n)
            assert cleaned is not None, f"clean returned None for: {n}"
            assert is_valid_person_name(cleaned) is True, f"is_valid failed for: {cleaned}"

    def test_all_caps_names(self):
        names = ["JOHN SMITH", "SARAH CONNOR", "ALEXANDER HAMILTON"]
        for n in names:
            assert is_valid_person_name(n) is True, f"is_valid failed for: {n}"

    def test_accented_names(self):
        names = ["Renée Dupont", "François Müller", "José Silva", "Björn Borg"]
        for n in names:
            cleaned = clean_person_name(n)
            assert cleaned is not None, f"clean returned None for: {n}"
            assert is_valid_person_name(cleaned) is True, f"is_valid failed for: {cleaned}"

    def test_name_suffixes_stripped(self):
        names = ["Martin Luther King, Jr.", "Robert Downey Jr.", "Thurston Howell III", "John Smith Sr."]
        for n in names:
            cleaned = clean_person_name(n)
            assert cleaned is not None, f"clean returned None for: {n}"
            assert "Jr" not in cleaned and "III" not in cleaned and "Sr" not in cleaned, f"Suffix not stripped: {cleaned}"
            assert is_valid_person_name(cleaned) is True, f"is_valid failed for: {cleaned}"
