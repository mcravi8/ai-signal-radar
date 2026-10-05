from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from pipeline.models import SourceItem
from pipeline.normalize import compact_text


COLLECTOR_USER_AGENT = "ai-signal-radar/0.1 (public research dashboard; https://github.com/mcravi8/ai-signal-radar)"
BROWSER_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class _IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._label = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        values = {key.casefold(): value or "" for key, value in attrs}
        self._href = values.get("href", "")
        self._label = values.get("aria-label", "") or values.get("title", "")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or not self._href:
            return
        title = compact_text(html.unescape(self._label or " ".join(self._text)))
        self.links.append((self._href, title))
        self._href = ""
        self._label = ""
        self._text = []


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.published_at = ""
        self._in_title = False
        self._json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        name = tag.casefold()
        if name == "title":
            self._in_title = True
        elif name == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            content = compact_text(html.unescape(values.get("content", "")))
            if key == "og:title" and content:
                self.title = content
            elif key in {"description", "og:description"} and content and not self.description:
                self.description = content
            elif key in {"article:published_time", "date", "datepublished"} and content:
                self.published_at = content
        elif name == "time" and values.get("datetime") and not self.published_at:
            self.published_at = compact_text(values["datetime"])
        elif name == "script" and values.get("type", "").casefold() == "application/ld+json":
            self._json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        name = tag.casefold()
        if name == "title":
            self._in_title = False
        elif name == "script" and self._json_ld:
            self._json_ld = False
            try:
                payload = json.loads("".join(self._json_ld_parts))
            except (TypeError, ValueError):
                return
            values = payload if isinstance(payload, list) else [payload]
            for value in values:
                if not isinstance(value, dict):
                    continue
                if not self.title and value.get("headline"):
                    self.title = compact_text(str(value["headline"]))
                if not self.description and value.get("description"):
                    self.description = compact_text(str(value["description"]))
                if not self.published_at and value.get("datePublished"):
                    self.published_at = compact_text(str(value["datePublished"]))

    def handle_data(self, data: str) -> None:
        if self._in_title and not self.title:
            self.title = compact_text(html.unescape(data))
        if self._json_ld:
            self._json_ld_parts.append(data)


def _fetch(url: str) -> bytes:
    headers = {
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
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


def parse_links(payload: bytes, base_url: str) -> list[tuple[str, str]]:
    parser = _IndexParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    unique: dict[str, str] = {}
    for href, title in parser.links:
        url = urllib.parse.urljoin(base_url, href).split("#", 1)[0]
        if url not in unique or (not unique[url] and title):
            unique[url] = title
    return list(unique.items())


def page_metadata(payload: bytes) -> tuple[str, str, str]:
    parser = _MetadataParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser.title, parser.description, parser.published_at


def _title_from_url(url: str) -> str:
    slug = urllib.parse.unquote(urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])
    return compact_text(re.sub(r"[-_]+", " ", slug)).title()


def collect(
    source_id: str,
    source_type: str,
    index_url: str,
    include_prefixes: list[str],
    limit: int = 30,
    include_patterns: list[str] | None = None,
) -> list[SourceItem]:
    compiled_patterns = [re.compile(pattern) for pattern in include_patterns or []]
    candidates = [
        (url, title)
        for url, title in parse_links(_fetch(index_url), index_url)
        if any(url.startswith(prefix) and url.rstrip("/") != prefix.rstrip("/") for prefix in include_prefixes)
        and (not compiled_patterns or any(pattern.search(url) for pattern in compiled_patterns))
    ]
    if not candidates:
        raise ValueError("official HTML index contained no matching issue links")

    items = []
    for url, index_title in candidates[:limit]:
        title = index_title or _title_from_url(url)
        description = ""
        published_at = ""
        try:
            page_title, description, published_at = page_metadata(_fetch(url))
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
                published_at=published_at,
                summary=description[:1200],
            )
        )
    return items
