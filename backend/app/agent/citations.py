"""Check the answer's citations against the evidence.

LLMs sometimes garble or invent arXiv IDs ("2-407.01219", or an ID that was never
retrieved). Every bracketed ID is repaired if it is a mangled copy of a real
source ID, and removed if it isn't one of the sources at all.
"""

import re

# A bracket that looks like a citation: [2005.11401], [2005.11401, 2404.16130], [arXiv:2-407.01219]
CITATION = re.compile(r"\s?\[([^\[\]]*\d{1,4}[.\-]?\d*\.\d{4,5}[^\[\]]*)\](?!\()")
ARXIV_ID = re.compile(r"\d{4}\.\d{4,5}")
PLACEHOLDER = re.compile(r"\s?\[arxiv[_ ]id\]", re.IGNORECASE)


def validate(text: str, known_ids: set[str]) -> tuple[str, list[str]]:
    """Return (cleaned text, cited IDs in first-seen order)."""
    cited: list[str] = []

    def fix(match: re.Match) -> str:
        ids = []
        for part in re.split(r"[,;]", match.group(1)):
            candidate = re.sub(r"[^\d.]", "", part.split(":")[-1])
            if ARXIV_ID.fullmatch(candidate) and candidate in known_ids and candidate not in ids:
                ids.append(candidate)
        for i in ids:
            if i not in cited:
                cited.append(i)
        return f" [{', '.join(ids)}]" if ids else ""

    text = CITATION.sub(fix, text)
    return PLACEHOLDER.sub("", text).strip(), cited
