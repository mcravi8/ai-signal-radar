from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import SourceItem


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def merge_items(path: Path, items: Iterable[SourceItem]) -> int:
    existing = {row["id"]: row for row in read_jsonl(path)}
    before = len(existing)
    for item in items:
        row = item.to_dict()
        if item.source_type == "company-directory" and existing.get(item.id, {}).get("published_at"):
            row["published_at"] = existing[item.id]["published_at"]
        existing[item.id] = row
    write_jsonl(path, sorted(existing.values(), key=lambda row: (row.get("published_at", ""), row["id"])))
    return len(existing) - before
