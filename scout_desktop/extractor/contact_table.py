"""Read header-labelled contact tables when the capture preserves column boundaries."""
from .models import EntityCluster, Observation
from .patterns import (is_valid_person_name, is_valid_company_name, is_plausible_title,
                       is_valid_email, is_valid_location, is_plausible_school)


_FIELDS = {
    "company": ("WORKS_AT", is_valid_company_name),
    "employer": ("WORKS_AT", is_valid_company_name),
    "job title": ("HAS_TITLE", is_plausible_title),
    "title": ("HAS_TITLE", is_plausible_title),
    "location": ("LOCATED_IN", is_valid_location),
    "school": ("STUDIED_AT", is_plausible_school),
    "university": ("STUDIED_AT", is_plausible_school),
    "email": ("HAS_EMAIL", is_valid_email),
}


def extract_contact_table(lines, capture_id, source_url):
    """None means no recognized table. An empty list means no usable rows."""
    for index, line in enumerate(lines):
        headers = [cell.strip().casefold() for cell in line.split("\t")]
        names = [i for i, h in enumerate(headers) if h in {"name", "full name", "candidate name", "contact name"}]
        if len(names) != 1 or not any(h in _FIELDS for h in headers):
            continue
        clusters = []
        for row in lines[index + 1:]:
            if "\t" not in row:
                break
            cells = [cell.strip() for cell in row.split("\t")]
            if len(cells) != len(headers):
                continue
            name = cells[names[0]]
            if not is_valid_person_name(name):
                continue
            cluster = EntityCluster(name)
            for header, value in zip(headers, cells):
                if value and header in _FIELDS:
                    predicate, valid = _FIELDS[header]
                    if valid(value):
                        cluster.add_observation(Observation("PERSON", name, predicate, value,
                            evidence=f"{name} | {header}: {value}", capture_id=capture_id, source_url=source_url))
            if cluster.observations:
                clusters.append(cluster)
        return clusters
    return None
