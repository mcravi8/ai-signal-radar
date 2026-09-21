from __future__ import annotations

import json
from pathlib import Path

from pipeline.export_public import BLOCKED_KEYS, PublicDataError
from pipeline.models import SourceItem


def collect(path: Path) -> list[SourceItem]:
    """Import an already-sanitized newsletter export; raw mailbox formats are rejected."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("items", [])
    items: list[SourceItem] = []
    for record in records:
        blocked = BLOCKED_KEYS.intersection(record)
        if blocked or "body" in record or "from" in record or "to" in record:
            raise PublicDataError("Email import must be sanitized before it enters the repository")
        items.append(SourceItem(**record))
    return items
