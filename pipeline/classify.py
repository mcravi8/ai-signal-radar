from __future__ import annotations

from collections.abc import Mapping


def classify_text(text: str, keywords: Mapping[str, list[str]]) -> list[str]:
    haystack = text.casefold()
    matches = []
    for theme_id, terms in keywords.items():
        if any(term.casefold() in haystack for term in terms):
            matches.append(theme_id)
    return sorted(matches)
