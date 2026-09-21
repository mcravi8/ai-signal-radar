from __future__ import annotations

from collections.abc import Iterable

from .normalize import canonical_url, compact_text


def deduplicate(rows: Iterable[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    result: list[dict] = []
    for row in rows:
        key = (canonical_url(row.get("url", "")), compact_text(row.get("title", "")).casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result
