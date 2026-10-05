from __future__ import annotations

import hashlib
import html
import re
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
COLLECTOR_USER_AGENT = "ai-signal-radar/0.1 (public research dashboard; https://github.com/mcravi8/ai-signal-radar)"
BROWSER_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "title":
            self._in_title = True
        if tag.casefold() != "meta":
            return
        key = (values.get("property") or values.get("name") or "").casefold()
        content = values.get("content", "")
        if key == "og:title" and content:
            self.title = compact_text(html.unescape(content))
        elif key in {"description", "og:description"} and content and not self.description:
            self.description = compact_text(html.unescape(content))

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and not self.title:
            self.title = compact_text(html.unescape(data))


def _fetch(url: str) -> bytes:
    headers = {
        "Accept": "application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "User-Agent": COLLECTOR_USER_AGENT,
    }
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 403:
            raise
    retry = urllib.request.Request(url, headers={**headers, "User-Agent": BROWSER_USER_AGENT})
    with urllib.request.urlopen(retry, timeout=30) as response:
        return response.read()


def parse(payload: bytes) -> tuple[list[tuple[str, str]], list[str]]:
    root = ET.fromstring(payload.lstrip(b"\xef\xbb\xbf \t\r\n"))
    urls = [
        (compact_text(node.findtext(f"{SITEMAP}loc", "")), compact_text(node.findtext(f"{SITEMAP}lastmod", "")))
        for node in root.findall(f"{SITEMAP}url")
    ]
    children = [compact_text(node.findtext(f"{SITEMAP}loc", "")) for node in root.findall(f"{SITEMAP}sitemap")]
    return [(url, updated) for url, updated in urls if url], [url for url in children if url]


def page_metadata(payload: bytes) -> tuple[str, str]:
    parser = _PageMetadataParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser.title, parser.description


def _title_from_url(url: str) -> str:
    slug = urllib.parse.unquote(urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])
    return compact_text(re.sub(r"[-_]+", " ", slug)).title()


def collect(
    source_id: str,
    source_type: str,
    sitemap_url: str,
    include_prefixes: list[str],
    limit: int = 30,
    include_patterns: list[str] | None = None,
    fallback_html_url: str = "",
) -> list[SourceItem]:
    try:
        records, child_sitemaps = parse(_fetch(sitemap_url))
    except Exception as sitemap_error:
        if not fallback_html_url:
            raise
        from . import html_index

        try:
            return html_index.collect(
                source_id,
                source_type,
                fallback_html_url,
                include_prefixes,
                limit,
                include_patterns or [],
            )
        except Exception as html_error:
            raise RuntimeError(
                f"Sitemap collection failed ({sitemap_error}); official HTML fallback failed ({html_error})"
            ) from html_error
    for child_url in child_sitemaps:
        child_records, _ = parse(_fetch(child_url))
        records.extend(child_records)

    compiled_patterns = [re.compile(pattern) for pattern in include_patterns or []]
    candidates = [
        (url, updated)
        for url, updated in records
        if any(url.startswith(prefix) and url.rstrip("/") != prefix.rstrip("/") for prefix in include_prefixes)
        and (not compiled_patterns or any(pattern.search(url) for pattern in compiled_patterns))
    ]
    candidates.sort(key=lambda record: (record[1], record[0]), reverse=True)

    items = []
    for url, updated in candidates[:limit]:
        title = _title_from_url(url)
        description = ""
        try:
            page_title, description = page_metadata(_fetch(url))
            title = page_title or title
        except Exception:
            pass
        digest = hashlib.sha256(url.encode()).hexdigest()[:20]
        items.append(
            SourceItem(
                id=f"{source_id}:{digest}",
                source_id=source_id,
                source_type=source_type,
                title=title,
                url=url,
                published_at=updated,
                summary=description[:1200],
            )
        )
    return items
