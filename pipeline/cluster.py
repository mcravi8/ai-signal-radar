from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


def group_by_theme(rows: Iterable[dict]) -> dict[str, list[dict]]:
    """Deterministic first pass; semantic clustering can replace this contract later."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        for theme_id in row.get("theme_ids", []):
            groups[theme_id].append(row)
    return dict(groups)
