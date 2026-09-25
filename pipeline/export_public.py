from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BLOCKED_KEYS = {
    "raw_body",
    "html_body",
    "mime",
    "oauth_token",
    "refresh_token",
    "authorization",
    "cookie",
    "gmail_message_id",
    "mailbox_id",
}

SENSITIVE_PATTERNS = {
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "Gmail account link": re.compile(r"mail\.google\.com/.*(?:authuser|#all/)", re.I),
    "bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

PUBLIC_ITEM_FIELD_ORDER = (
    "id",
    "source_id",
    "source_type",
    "title",
    "url",
    "published_at",
    "summary",
    "authors",
    "tags",
    "projects",
    "sponsor_status",
    "theme_ids",
    "classification_disposition",
    "classification_reason",
    "classification_rule_id",
    "verification",
)
PUBLIC_ITEM_FIELDS = set(PUBLIC_ITEM_FIELD_ORDER)


VERIFICATION_FIELDS = {
    "repository": {"stars", "forks", "pushed_at", "license"},
    "company-directory": {"batch", "status", "team_size", "location", "github_url", "date_basis"},
    "job-posting": {"company", "batch", "role", "location", "created_at", "date_basis"},
}


class PublicDataError(ValueError):
    pass


def sanitize_item(row: dict[str, Any]) -> dict[str, Any]:
    blocked = BLOCKED_KEYS.intersection(row)
    if blocked:
        raise PublicDataError(f"Blocked fields present: {', '.join(sorted(blocked))}")
    clean = {key: row[key] for key in PUBLIC_ITEM_FIELD_ORDER if key in row}
    allowed = VERIFICATION_FIELDS.get(row.get("source_type", ""), set())
    metadata = row.get("metadata", {})
    verification = {key: metadata[key] for key in allowed if metadata.get(key) is not None}
    if verification:
        clean["verification"] = verification
    return clean


def validate_public_payload(payload: Any) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(serialized):
            raise PublicDataError(f"Possible {label} found in public payload")

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            blocked = BLOCKED_KEYS.intersection(value)
            if blocked:
                raise PublicDataError(f"Blocked public keys: {', '.join(sorted(blocked))}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)


def write_public_dashboard(path: Path, payload: dict[str, Any]) -> None:
    validate_public_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
