from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pipeline.models import SourceItem


def collect(limit: int = 50) -> list[SourceItem]:
    local_cli = Path(sys.executable).with_name("hf")
    executable = str(local_cli) if local_cli.exists() else "hf"
    command = [executable, "papers", "list", "--sort", "trending", "--limit", str(limit), "--format", "json"]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    records = payload if isinstance(payload, list) else payload.get("items", payload.get("papers", []))
    items: list[SourceItem] = []
    for record in records:
        paper_id = str(record.get("id") or record.get("paperId") or record.get("arxivId") or "")
        if not paper_id:
            continue
        items.append(
            SourceItem(
                id=f"hf-paper:{paper_id}",
                source_id="huggingface-papers",
                source_type="paper-curation",
                title=record.get("title", "Untitled paper"),
                url=f"https://huggingface.co/papers/{paper_id}",
                published_at=str(record.get("publishedAt") or record.get("published_at") or ""),
                summary=str(record.get("summary") or record.get("abstract") or "")[:1200],
                authors=[str(author) for author in record.get("authors", []) if author],
                metadata={"upvotes": record.get("upvotes")},
            )
        )
    return items
