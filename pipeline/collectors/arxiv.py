from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from pipeline.models import SourceItem
from pipeline.normalize import compact_text

ATOM = "{http://www.w3.org/2005/Atom}"
RETRYABLE_STATUS_CODES = {406, 408, 425, 429, 500, 502, 503, 504}


def _fetch(url: str, attempts: int = 4) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/atom+xml, application/xml;q=0.9, */*;q=0.8",
            "User-Agent": "ai-signal-radar/0.1 (public research dashboard; https://github.com/mcravi8/ai-signal-radar)",
        },
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(min(delay, 15))
        except (TimeoutError, urllib.error.URLError):
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("arXiv request exhausted without returning a response")


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
    root = ET.fromstring(_fetch(f"https://export.arxiv.org/api/query?{params}"))

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
