from __future__ import annotations

import hashlib
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return compact_text(html.unescape(without_tags))


def _date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.isoformat()
    except (TypeError, ValueError):
        return value


def parse(source_id: str, source_type: str, payload: bytes, limit: int = 30) -> list[SourceItem]:
    root = ET.fromstring(payload)
    records = root.findall("./channel/item")
    atom = False
    if not records:
        records = root.findall(f"{ATOM}entry")
        atom = True

    items = []
    for record in records[:limit]:
        if atom:
            title = compact_text(record.findtext(f"{ATOM}title", ""))
            link_node = record.find(f"{ATOM}link")
            url = (link_node.attrib.get("href", "") if link_node is not None else "").strip()
            published = record.findtext(f"{ATOM}published", "") or record.findtext(f"{ATOM}updated", "")
            summary = record.findtext(f"{ATOM}summary", "") or record.findtext(f"{ATOM}content", "")
            author = compact_text(record.findtext(f"{ATOM}author/{ATOM}name", ""))
            identifier = record.findtext(f"{ATOM}id", "") or url
        else:
            title = compact_text(record.findtext("title", ""))
            url = compact_text(record.findtext("link", ""))
            published = _date(record.findtext("pubDate", ""))
            summary = record.findtext("description", "") or ""
            author = compact_text(record.findtext(f"{DC}creator", "") or record.findtext("author", ""))
            identifier = record.findtext("guid", "") or url
        if not title or not url:
            continue
        digest = hashlib.sha256((identifier or url).encode()).hexdigest()[:20]
        items.append(
            SourceItem(
                id=f"{source_id}:{digest}",
                source_id=source_id,
                source_type=source_type,
                title=title,
                url=url,
                published_at=published,
                summary=_plain_text(summary)[:1200],
                authors=[author] if author else [],
            )
        )
    return items


def collect(source_id: str, source_type: str, feed_url: str, limit: int = 30) -> list[SourceItem]:
    request = urllib.request.Request(
        feed_url,
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
            "User-Agent": "ai-signal-radar/0.1 (public research dashboard; https://github.com/mcravi8/ai-signal-radar)",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse(source_id, source_type, response.read(), limit)
