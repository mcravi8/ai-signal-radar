from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PUBLIC_DISPOSITIONS = {"classified", "classification-review", "out-of-scope"}


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


def validate_classification_policy(policy: Mapping[str, Any]) -> None:
    dispositions = set(policy.get("dispositions", {}))
    if dispositions != PUBLIC_DISPOSITIONS:
        raise ValueError("Classification dispositions do not match the public contract")
    if not policy.get("scope_definition") or not policy.get("scope_terms"):
        raise ValueError("Classification policy requires a scope definition and scope terms")
    seen: set[str] = set()
    for rule in policy.get("out_of_scope_rules", []):
        rule_id = rule.get("id", "")
        if not rule_id or rule_id in seen:
            raise ValueError(f"Out-of-scope rule id is missing or duplicated: {rule_id!r}")
        seen.add(rule_id)
        if not rule.get("reason"):
            raise ValueError(f"Out-of-scope rule {rule_id} requires a public reason")
        if not any(rule.get(field) for field in ("source_ids", "source_types", "title_patterns")):
            raise ValueError(f"Out-of-scope rule {rule_id} is unbounded")
        for pattern in rule.get("title_patterns", []):
            re.compile(pattern, re.I)


def _matches_out_of_scope_rule(
    row: Mapping[str, Any],
    searchable: str,
    rule: Mapping[str, Any],
    scope_terms: list[str],
) -> bool:
    source_ids = set(rule.get("source_ids", []))
    source_types = set(rule.get("source_types", []))
    if source_ids and row.get("source_id") not in source_ids:
        return False
    if source_types and row.get("source_type") not in source_types:
        return False
    patterns = rule.get("title_patterns", [])
    if patterns and not any(re.search(pattern, row.get("title", ""), re.I) for pattern in patterns):
        return False
    if rule.get("requires_no_scope_term") and any(
        _matches_term(searchable, term) for term in scope_terms
    ):
        return False
    return True


def classify_record(
    row: Mapping[str, Any],
    keywords: Mapping[str, list[str]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    searchable = " ".join(
        [
            row.get("title", ""),
            row.get("summary", ""),
            " ".join(row.get("tags", [])),
        ]
    ).casefold()
    theme_ids = classify_text(searchable, keywords)
    if theme_ids:
        return {
            "theme_ids": theme_ids,
            "disposition": "classified",
            "reason": "Matched reviewed canonical-theme vocabulary.",
            "rule_id": "canonical-theme-match",
        }
    scope_terms = list(policy.get("scope_terms", []))
    for rule in policy.get("out_of_scope_rules", []):
        if _matches_out_of_scope_rule(row, searchable, rule, scope_terms):
            return {
                "theme_ids": [],
                "disposition": "out-of-scope",
                "reason": rule["reason"],
                "rule_id": rule["id"],
            }
    return {
        "theme_ids": [],
        "disposition": "classification-review",
        "reason": "No canonical theme matched and no reviewed exclusion rule applies.",
        "rule_id": "unresolved-review",
    }
