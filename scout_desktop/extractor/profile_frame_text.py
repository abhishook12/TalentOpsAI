"""Recover missing text from the visible profile while preserving line order."""
import re
from typing import List


def supplement_profile_text(
    browser_lines: List[str], image_lines: List[str], person_name: str
) -> List[str]:
    """
    Recover profile header lines from OCR, scoped to the same named person.

    Extracts fields from each source in its original order, then combines
    fields belonging to the same profile so employer/school order is preserved
    and the school beneath an 'Education' heading is not missed.
    """
    if not person_name or not image_lines:
        return browser_lines

    name = " ".join(person_name.split())
    heading = re.compile(
        re.escape(name)
        + r"(?:\s*(?:[·•@|✓✔]|he/him\b|she/her\b|they/them\b|[123](?:st|nd|rd)\b).*)?$",
        re.I,
    )
    # Stop only at distinct post-header sections or external widgets.
    # Crucially, 'education' is excluded from termination headings so any
    # school listed under an 'Education' section heading is retained.
    end = re.compile(
        r"^(?:more profiles for you|people you may know|people also viewed|promoted|activity|about|experience|recommendations|skills|interests)(?:\s*[·•:].*)?$",
        re.I,
    )

    key = lambda value: " ".join(value.split()).casefold()

    for index, line in enumerate(image_lines):
        if heading.fullmatch(" ".join(line.split())):
            header = []
            for following in image_lines[index + 1 : index + 31]:
                if end.fullmatch(following.strip()):
                    break
                header.append(following)

            if not header:
                return browser_lines

            # Find person heading in browser_lines
            start_pos = -1
            for pos, value in enumerate(browser_lines):
                if heading.fullmatch(" ".join(value.split())):
                    start_pos = pos
                    break

            if start_pos == -1:
                seen = {key(t) for t in [line, *header]}
                return [
                    line,
                    *header,
                    *(v for v in browser_lines if key(v) not in seen),
                ]

            # Combine fields in their original order without scrambling:
            # Anchor each item after its predecessor in the candidate card
            result = list(browser_lines)
            anchor = start_pos

            for item in header:
                k = key(item)
                if not k:
                    continue

                # Check if item already exists at or after anchor
                existing_idx = -1
                for idx in range(anchor, len(result)):
                    if key(result[idx]) == k:
                        existing_idx = idx
                        break

                if existing_idx != -1:
                    anchor = existing_idx
                else:
                    # Check if already present before anchor in profile card
                    found_before = any(
                        key(result[idx]) == k for idx in range(start_pos, anchor)
                    )
                    if not found_before:
                        anchor += 1
                        result.insert(anchor, item)

            return result

    return browser_lines
