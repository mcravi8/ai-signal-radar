from __future__ import annotations

import re
from collections.abc import Mapping


def _matches_term(haystack: str, term: str) -> bool:
    """Match taxonomy vocabulary as a term, not as an arbitrary substring."""
    normalized = term.casefold().strip()
    if not normalized:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", haystack) is not None


def classify_text(text: str, keywords: Mapping[str, list[str]]) -> list[str]:
    haystack = text.casefold()
    matches = []
    for theme_id, terms in keywords.items():
        if any(_matches_term(haystack, term) for term in terms):
            matches.append(theme_id)
    return sorted(matches)
