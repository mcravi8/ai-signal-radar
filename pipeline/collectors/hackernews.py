from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

from pipeline.models import SourceItem
from pipeline.normalize import compact_text

BASE = "https://hacker-news.firebaseio.com/v0"


def _json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "ai-signal-radar/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def collect(feeds: list[str], per_feed: int = 30) -> list[SourceItem]:
    items: list[SourceItem] = []
    seen: set[int] = set()
    for feed in feeds:
        for item_id in (_json(f"{BASE}/{feed}.json") or [])[:per_feed]:
            if item_id in seen:
                continue
            seen.add(item_id)
            record = _json(f"{BASE}/item/{item_id}.json") or {}
            if record.get("deleted") or record.get("dead"):
                continue
            url = record.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
            published = datetime.fromtimestamp(record.get("time", 0), tz=timezone.utc).isoformat()
            items.append(
                SourceItem(
                    id=f"hn:{item_id}",
                    source_id="hacker-news",
                    source_type="community",
                    title=compact_text(record.get("title") or "Hacker News discussion"),
                    url=url,
                    published_at=published,
                    summary=compact_text(record.get("text") or "")[:1200],
                    authors=[record.get("by", "")],
                    metadata={"score": record.get("score", 0), "comments": record.get("descendants", 0), "feed": feed},
                )
            )
    return items
