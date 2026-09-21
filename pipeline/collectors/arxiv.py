from __future__ import annotations

import hashlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from pipeline.models import SourceItem
from pipeline.normalize import compact_text

ATOM = "{http://www.w3.org/2005/Atom}"


def collect(categories: list[str], limit: int = 100) -> list[SourceItem]:
    query = " OR ".join(f"cat:{category}" for category in categories)
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(
        f"https://export.arxiv.org/api/query?{params}",
        headers={"User-Agent": "ai-signal-radar/0.1 (public research dashboard)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    items: list[SourceItem] = []
    for entry in root.findall(f"{ATOM}entry"):
        url = compact_text(entry.findtext(f"{ATOM}id", ""))
        title = compact_text(entry.findtext(f"{ATOM}title", ""))
        identifier = url.rsplit("/", 1)[-1] or hashlib.sha256(url.encode()).hexdigest()[:16]
        items.append(
            SourceItem(
                id=f"arxiv:{identifier}",
                source_id="arxiv",
                source_type="paper",
                title=title,
                url=url,
                published_at=compact_text(entry.findtext(f"{ATOM}published", "")),
                summary=compact_text(entry.findtext(f"{ATOM}summary", ""))[:1200],
                authors=[compact_text(author.findtext(f"{ATOM}name", "")) for author in entry.findall(f"{ATOM}author")],
                tags=[node.attrib.get("term", "") for node in entry.findall(f"{ATOM}category")],
            )
        )
    return items
